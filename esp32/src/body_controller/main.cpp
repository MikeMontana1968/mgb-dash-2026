/**
 * MGB Dash 2026 — Body Controller Main
 *
 * Reads vehicle sensor states, hall sensor for speed/odometer,
 * estimates gear, broadcasts on CAN, serves BLE.
 */

#include <Arduino.h>
#include "esp_log.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LeafCan.h"
#include "can_ids.h"
#include <Preferences.h>
#include <cstring>
#include <cmath>

static const char* TAG = GAUGE_ROLE_NAME;

CanBus canBus;
Heartbeat heartbeat;
CanLog canLog;
LeafCan leafCan;
Preferences prefs;

// ── Drivetrain constants (compile-time) ─────────────────────────────
static constexpr double MILES_PER_PULSE =
    (TIRE_DIAMETER_IN * M_PI) / (HALL_MAGNETS_PER_REV * DIFF_RATIO * 63360.0);

// ── Hall sensor state ───────────────────────────────────────────────
volatile uint32_t hallPulseCount = 0;
volatile unsigned long lastHallPulseUs = 0;

void IRAM_ATTR hallISR() {
    hallPulseCount++;
    lastHallPulseUs = micros();
}

// ── Speed computation ───────────────────────────────────────────────
uint32_t prevPulseCount = 0;
unsigned long prevSpeedMs = 0;
double speedMph = 0.0;
static constexpr unsigned long SPEED_ZERO_TIMEOUT_US = 500000;  // 500ms no pulse → 0

// ── Gear estimation ─────────────────────────────────────────────────
int16_t motorRpm = 0;
uint8_t currentGear = GEAR_UNKNOWN;

// ── Odometer ────────────────────────────────────────────────────────
double odometerMiles = 0.0;
double odometerSinceLastPersist = 0.0;

// ── Hazard detection state machine ──────────────────────────────────
bool leftActive  = false;
bool rightActive = false;
unsigned long leftOnMs  = 0;
unsigned long rightOnMs = 0;
static constexpr unsigned long HAZARD_WINDOW_MS = 50;

// ── GPIO / body flags ───────────────────────────────────────────────
uint8_t bodyFlags = 0;
bool prevKeyOn = false;

// ── Timing ──────────────────────────────────────────────────────────
unsigned long lastStateMs = 0;   // 10 Hz: 0x710 + 0x711
unsigned long lastGearMs  = 0;   // 2 Hz:  0x712
unsigned long lastOdoMs   = 0;   // 1 Hz:  0x713

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode = false;

// ═════════════════════════════════════════════════════════════════════
// Helper: Read GPIOs and build body flags with hazard detection
// ═════════════════════════════════════════════════════════════════════
void readGPIO(unsigned long now) {
    // Optocouplers are active-low → invert
    bool keyOn   = !digitalRead(PIN_KEY_ON);
    bool brake   = !digitalRead(PIN_BRAKE);
    bool regen   = !digitalRead(PIN_REGEN);
    bool fan     = !digitalRead(PIN_FAN);
    bool reverse = !digitalRead(PIN_REVERSE);
    bool left    = !digitalRead(PIN_LEFT_TURN);
    bool right   = !digitalRead(PIN_RIGHT_TURN);

    // Build base flags
    bodyFlags = 0;
    if (keyOn)   bodyFlags |= BODY_FLAG_KEY_ON;
    if (brake)   bodyFlags |= BODY_FLAG_BRAKE;
    if (regen)   bodyFlags |= BODY_FLAG_REGEN;
    if (fan)     bodyFlags |= BODY_FLAG_FAN;
    if (reverse) bodyFlags |= BODY_FLAG_REVERSE;

    // ── Hazard detection ────────────────────────────────────────────
    // Track off→on transitions
    if (left && !leftActive)   leftOnMs = now;
    if (right && !rightActive) rightOnMs = now;
    leftActive  = left;
    rightActive = right;

    if (left && right) {
        unsigned long delta = (leftOnMs > rightOnMs)
            ? (leftOnMs - rightOnMs) : (rightOnMs - leftOnMs);
        if (delta <= HAZARD_WINDOW_MS) {
            bodyFlags |= BODY_FLAG_HAZARD;
        } else {
            bodyFlags |= BODY_FLAG_LEFT_TURN;
            bodyFlags |= BODY_FLAG_RIGHT_TURN;
        }
    } else {
        if (left)  bodyFlags |= BODY_FLAG_LEFT_TURN;
        if (right) bodyFlags |= BODY_FLAG_RIGHT_TURN;
    }

    // ── Key on/off edge detection ───────────────────────────────────
    if (keyOn && !prevKeyOn) {
        canLog.log(LogLevel::LOG_INFO, LogEvent::KEY_ON);
        ESP_LOGI(TAG, "Key ON");
    } else if (!keyOn && prevKeyOn) {
        canLog.log(LogLevel::LOG_INFO, LogEvent::KEY_OFF);
        ESP_LOGI(TAG, "Key OFF");
    }
    prevKeyOn = keyOn;
}

// ═════════════════════════════════════════════════════════════════════
// Helper: Compute speed from hall sensor
// ═════════════════════════════════════════════════════════════════════
void computeSpeed(unsigned long nowMs) {
    // Snapshot volatile state with interrupts disabled
    noInterrupts();
    uint32_t pulses = hallPulseCount;
    unsigned long lastPulseUs = lastHallPulseUs;
    interrupts();

    uint32_t pulseDelta = pulses - prevPulseCount;
    unsigned long timeDeltaMs = nowMs - prevSpeedMs;

    // Update odometer
    double distDelta = pulseDelta * MILES_PER_PULSE;
    odometerMiles += distDelta;
    odometerSinceLastPersist += distDelta;

    if (timeDeltaMs > 0 && pulseDelta > 0) {
        double pulsesPerSec = (double)pulseDelta / ((double)timeDeltaMs / 1000.0);
        speedMph = pulsesPerSec * MILES_PER_PULSE * 3600.0;
    } else if (pulseDelta == 0) {
        // No pulses in this window — check timeout
        unsigned long elapsedUs = micros() - lastPulseUs;
        if (lastPulseUs == 0 || elapsedUs > SPEED_ZERO_TIMEOUT_US) {
            speedMph = 0.0;
        }
        // else: keep previous speed during brief gap
    }

    prevPulseCount = pulses;
    prevSpeedMs = nowMs;

    ESP_LOGI(TAG, "Speed: %.1f mph, pulses: %lu, odo: %.1f mi",
             speedMph, (unsigned long)pulseDelta, odometerMiles);
}

// ═════════════════════════════════════════════════════════════════════
// Helper: Estimate gear from motor RPM and vehicle speed
// ═════════════════════════════════════════════════════════════════════
void estimateGear() {
    // In reverse — gear estimation not meaningful; reverse flag is in payload
    if (bodyFlags & BODY_FLAG_REVERSE) {
        currentGear = GEAR_NEUTRAL;
        return;
    }

    // Need both meaningful speed and motor RPM
    if (speedMph < 2.0 || abs(motorRpm) < 100) {
        currentGear = GEAR_NEUTRAL;
        return;
    }

    // Wheel RPM from speed
    double wheelCircIn = TIRE_DIAMETER_IN * M_PI;
    double wheelRpm = (speedMph * 63360.0) / (wheelCircIn * 60.0);
    double driveshaftRpm = wheelRpm * DIFF_RATIO;

    if (driveshaftRpm < 1.0) {
        currentGear = GEAR_NEUTRAL;
        return;
    }

    double ratio = fabs((double)motorRpm) / driveshaftRpm;

    // Compare ratio to each gear within ±GEAR_TOLERANCE (15%)
    static constexpr double gearRatios[] = {
        GEAR_RATIO_1, GEAR_RATIO_2, GEAR_RATIO_3, GEAR_RATIO_4
    };
    static constexpr uint8_t gearValues[] = {
        GEAR_1, GEAR_2, GEAR_3, GEAR_4
    };

    for (int i = 0; i < 4; i++) {
        if (fabs(ratio - gearRatios[i]) / gearRatios[i] <= GEAR_TOLERANCE) {
            currentGear = gearValues[i];
            return;
        }
    }

    currentGear = GEAR_UNKNOWN;
}

// ═════════════════════════════════════════════════════════════════════
// Helper: Persist odometer to NVS if threshold exceeded
// ═════════════════════════════════════════════════════════════════════
void persistOdoIfNeeded() {
    if (odometerSinceLastPersist >= ODO_PERSIST_MILES) {
        prefs.begin("odo", false);  // read-write
        prefs.putDouble("miles", odometerMiles);
        prefs.end();
        odometerSinceLastPersist = 0.0;
        ESP_LOGI(TAG, "Odometer persisted: %.1f miles", odometerMiles);
    }
}

// ═════════════════════════════════════════════════════════════════════
// Setup
// ═════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(115200);
    ESP_LOGI(TAG, "Body controller starting...");

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START);

    canBus.init(PIN_CAN_TX, PIN_CAN_RX, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);

    // Digital inputs
    pinMode(PIN_KEY_ON, INPUT);
    pinMode(PIN_BRAKE, INPUT);
    pinMode(PIN_REGEN, INPUT);
    pinMode(PIN_FAN, INPUT);
    pinMode(PIN_REVERSE, INPUT);
    pinMode(PIN_LEFT_TURN, INPUT);
    pinMode(PIN_RIGHT_TURN, INPUT);

    // Hall sensor (interrupt-driven)
    pinMode(PIN_HALL_SENSOR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_HALL_SENSOR), hallISR, FALLING);

    // Load persisted odometer from NVS
    prefs.begin("odo", true);  // read-only
    odometerMiles = prefs.getDouble("miles", 0.0);
    prefs.end();
    ESP_LOGI(TAG, "Odometer loaded: %.1f miles", odometerMiles);

    // Initialize speed timing baseline
    prevSpeedMs = millis();

    // TODO: Init BLE peripheral

    // ── Self-test (log only, no visual hardware on body controller) ──
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

// ═════════════════════════════════════════════════════════════════════
// Main loop
// ═════════════════════════════════════════════════════════════════════
void loop() {
    heartbeat.update();
    canBus.checkErrors();
    unsigned long now = millis();

    // ── CAN receive — drain queue ───────────────────────────────────
    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    while (canBus.receive(id, data, len)) {
        canMessageReceived = true;
        if (id == CAN_ID_LEAF_MOTOR_STATUS) {
            MotorStatus ms = LeafCan::decodeMotorStatus(data);
            motorRpm = ms.rpm;
        } else if (id == CAN_ID_SELF_TEST) {
            if (data[0] == SELF_TEST_TARGET_ALL ||
                data[0] == static_cast<uint8_t>(LogRole::BODY)) {
                canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
                canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);
                ESP_LOGI(TAG, "Self-test triggered (log only)");
            }
        }
    }

    // ── 10 Hz: state + speed ────────────────────────────────────────
    if (now - lastStateMs >= 100) {
        lastStateMs = now;

        readGPIO(now);

        // Broadcast BODY_STATE (0x710)
        uint8_t statePayload[8] = {};
        statePayload[0] = bodyFlags;
        canBus.safeTransmit(CAN_ID_BODY_STATE, statePayload, 8);

        computeSpeed(now);

        // Broadcast BODY_SPEED (0x711)
        uint8_t speedPayload[8] = {};
        memcpy(speedPayload, &speedMph, sizeof(double));
        canBus.safeTransmit(CAN_ID_BODY_SPEED, speedPayload, 8);
    }

    // ── 2 Hz: gear ──────────────────────────────────────────────────
    if (now - lastGearMs >= 500) {
        lastGearMs = now;

        estimateGear();
        ESP_LOGI(TAG, "Gear: %u, motorRPM: %d, speed: %.1f mph",
                 currentGear, motorRpm, speedMph);

        // Broadcast BODY_GEAR (0x712)
        uint8_t gearPayload[8] = {};
        gearPayload[0] = currentGear;
        gearPayload[1] = (bodyFlags & BODY_FLAG_REVERSE) ? 1 : 0;
        canBus.safeTransmit(CAN_ID_BODY_GEAR, gearPayload, 8);
    }

    // ── 1 Hz: odometer ──────────────────────────────────────────────
    if (now - lastOdoMs >= 1000) {
        lastOdoMs = now;

        // Broadcast BODY_ODOMETER (0x713) — uint32 little-endian miles
        uint32_t odoU32 = (uint32_t)odometerMiles;
        uint8_t odoPayload[8] = {};
        memcpy(odoPayload, &odoU32, sizeof(uint32_t));
        canBus.safeTransmit(CAN_ID_BODY_ODOMETER, odoPayload, 8);

        persistOdoIfNeeded();
    }

    // ── CAN silence watchdog ────────────────────────────────────────
    if (!canMessageReceived && millis() > CAN_SILENCE_TIMEOUT_MS) {
        if (!canSilenceMode) {
            canSilenceMode = true;
            canLog.log(LogLevel::LOG_WARN, LogEvent::CAN_SILENCE);
            ESP_LOGW(TAG, "CAN silence — no traffic within timeout");
        }
    }
    if (canMessageReceived && canSilenceMode) {
        canSilenceMode = false;
        canLog.log(LogLevel::LOG_INFO, LogEvent::BUS_RECOVERED);
        ESP_LOGI(TAG, "CAN traffic resumed");
    }

    delay(10);
}
