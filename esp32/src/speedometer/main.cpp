/**
 * MGB Dash 2026 — Speedometer Main
 *
 * CAN-driven mechanical speedometer:
 *   - 28BYJ-48 stepper needle (StepperWheel lib, cubic-eased)
 *   - Servo gear indicator disc (ServoGauge lib)
 *   - WS2812B LED ring (turn signals, hazards, ambient)
 *   - eInk odometer (future TODO)
 *
 * All speed/gear/odometer data comes from body controller via CAN —
 * no local sensor logic.
 */

#include <Arduino.h>
#include <cmath>
#include "esp_log.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LedRing.h"
#include "ServoGauge.h"
#include "StepperWheel.h"
#include "can_ids.h"

static const char* TAG = GAUGE_ROLE_NAME;

CanBus      canBus;
Heartbeat   heartbeat;
CanLog      canLog;
LedRing     ledRing;
ServoGauge  gearServo;
StepperWheel stepperWheel;

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode     = false;

// ── Turn signal / hazard holdoff ────────────────────────────────────
unsigned long lastLeftMs   = 0;
unsigned long lastRightMs  = 0;
unsigned long lastHazardMs = 0;
static constexpr unsigned long TURN_HOLDOFF_MS = 600;

enum AnimState { ANIM_NONE, ANIM_HAZARD, ANIM_LEFT, ANIM_RIGHT };
AnimState currentAnim = ANIM_NONE;

// ── Body state flags (from 0x710) ───────────────────────────────────
uint8_t lastBodyFlags = 0;

// ── Gear angle lookup ───────────────────────────────────────────────
// Servo angles for gear indicator disc
static constexpr int GEAR_ANGLES[] = {
    15,   // GEAR_NEUTRAL (0)
    30,   // GEAR_1 (1)
    45,   // GEAR_2 (2)
    60,   // GEAR_3 (3)
    75,   // GEAR_4 (4)
};
static constexpr int GEAR_ANGLE_REVERSE = 0;
static constexpr int GEAR_ANGLE_UNKNOWN = 15;  // show neutral

// ── Color wheel helper ──────────────────────────────────────────────
static void wheelToRGB(uint8_t pos, uint8_t &r, uint8_t &g, uint8_t &b) {
    if (pos < 85) {
        r = 255 - pos * 3;
        g = pos * 3;
        b = 0;
    } else if (pos < 170) {
        pos -= 85;
        r = 0;
        g = 255 - pos * 3;
        b = pos * 3;
    } else {
        pos -= 170;
        r = pos * 3;
        g = 0;
        b = 255 - pos * 3;
    }
}

// ═════════════════════════════════════════════════════════════════════
// Self-test: stepper sweep + LED chase + servo sweep
// ═════════════════════════════════════════════════════════════════════
void runSelfTest() {
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    ESP_LOGI(TAG, "Self-test starting...");

    const int degreesPerLed = 180 / LED_COUNT;

    // ── Phase 1: Servo sweep up + LED rainbow fill ──────────────────
    for (int a = 0; a <= 180; a += 2) {
        gearServo.writeDirect(a);

        int litCount = a / degreesPerLed;
        for (int i = 0; i < LED_COUNT; i++) {
            if (i <= litCount) {
                uint8_t r, g, b;
                wheelToRGB((i * 256) / LED_COUNT, r, g, b);
                ledRing.setPixel(i, r, g, b);
            } else {
                ledRing.setPixel(i, 0, 0, 0);
            }
        }
        ledRing.show();
        delay(8);
    }

    // ── Phase 2: Hold + white flash ─────────────────────────────────
    ledRing.setAll(255, 255, 255);
    ledRing.show();
    delay(150);
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t r, g, b;
        wheelToRGB((i * 256) / LED_COUNT, r, g, b);
        ledRing.setPixel(i, r, g, b);
    }
    ledRing.show();
    delay(150);

    // ── Phase 3: Servo sweep down + LEDs extinguish ─────────────────
    for (int a = 180; a >= 0; a -= 2) {
        gearServo.writeDirect(a);

        int litCount = a / degreesPerLed;
        for (int i = 0; i < LED_COUNT; i++) {
            if (i <= litCount) {
                uint8_t r, g, b;
                wheelToRGB((i * 256) / LED_COUNT, r, g, b);
                ledRing.setPixel(i, r, g, b);
            } else {
                ledRing.setPixel(i, 0, 0, 0);
            }
        }
        ledRing.show();
        delay(8);
    }

    // ── Phase 4: Stepper sweep 0→45→0 MPH ──────────────────────────
    if (stepperWheel.isCalibrated()) {
        stepperWheel.moveToMPH(45);
        while (stepperWheel.isInTransition()) {
            stepperWheel.update();
            delay(10);
        }
        stepperWheel.moveToMPH(0);
        while (stepperWheel.isInTransition()) {
            stepperWheel.update();
            delay(10);
        }
    }

    // ── Phase 5: Double green flash (pass indicator) ────────────────
    ledRing.setAll(0, 0, 0);
    ledRing.show();
    delay(100);
    for (int f = 0; f < 2; f++) {
        ledRing.setAll(0, 255, 0);
        ledRing.show();
        delay(150);
        ledRing.setAll(0, 0, 0);
        ledRing.show();
        delay(150);
    }

    gearServo.writeDirect(0);
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);
    ESP_LOGI(TAG, "Self-test complete.");
}

// ═════════════════════════════════════════════════════════════════════
// Turn signal / hazard animation (same pattern as servo_gauge)
// ═════════════════════════════════════════════════════════════════════
static void updateAnimations() {
    unsigned long now = millis();

    if (lastBodyFlags & BODY_FLAG_HAZARD)     lastHazardMs = now;
    if (lastBodyFlags & BODY_FLAG_LEFT_TURN)  lastLeftMs   = now;
    if (lastBodyFlags & BODY_FLAG_RIGHT_TURN) lastRightMs  = now;

    bool hazardActive = lastHazardMs > 0 && (now - lastHazardMs) < TURN_HOLDOFF_MS;
    bool leftActive   = lastLeftMs   > 0 && (now - lastLeftMs)   < TURN_HOLDOFF_MS;
    bool rightActive  = lastRightMs  > 0 && (now - lastRightMs)  < TURN_HOLDOFF_MS;

    AnimState desired = ANIM_NONE;
    if (hazardActive)      desired = ANIM_HAZARD;
    else if (leftActive)   desired = ANIM_LEFT;
    else if (rightActive)  desired = ANIM_RIGHT;

    if (desired != currentAnim) {
        switch (desired) {
            case ANIM_HAZARD: ledRing.startHazard();          break;
            case ANIM_LEFT:   ledRing.startTurnSignal(true);  break;
            case ANIM_RIGHT:  ledRing.startTurnSignal(false); break;
            case ANIM_NONE:   ledRing.stopAnimation();        break;
        }
        currentAnim = desired;
    }
}

// ═════════════════════════════════════════════════════════════════════
// Setup
// ═════════════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);

    char versionStr[48];
    snprintf(versionStr, sizeof(versionStr), "%s v%d.%s.%s",
             GAUGE_ROLE_NAME, VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    ESP_LOGI(TAG, "%s starting...", versionStr);

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START, 0, versionStr);

    canBus.init(PIN_CAN_TX, PIN_CAN_RX, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(PIN_LED_DATA, LED_COUNT);

    // ── Stepper needle ──────────────────────────────────────────────
    stepperWheel.init(PIN_STEPPER_IN1, PIN_STEPPER_IN2,
                      PIN_STEPPER_IN3, PIN_STEPPER_IN4,
                      PIN_STEPPER_HOME);

    bool homed = stepperWheel.calibrateHome();
    if (homed) {
        canLog.log(LogLevel::LOG_INFO, LogEvent::STEPPER_HOME_OK);
        ESP_LOGI(TAG, "Stepper homed successfully");
    } else {
        canLog.log(LogLevel::LOG_WARN, LogEvent::STEPPER_HOME_FAIL);
        ESP_LOGW(TAG, "Stepper homing FAILED — needle may be misaligned");
    }

    // ── Gear indicator servo ────────────────────────────────────────
    gearServo.init(PIN_SERVO);
    gearServo.setRange(0.0f, 90.0f);     // angle range for gear disc
    gearServo.setSmoothing(0.3f);         // snappy — gear changes are discrete

    // ── Self-test ───────────────────────────────────────────────────
    runSelfTest();

    // ── Park gear servo at neutral ──────────────────────────────────
    gearServo.setAngle(GEAR_ANGLES[GEAR_NEUTRAL]);

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

// ═════════════════════════════════════════════════════════════════════
// Loop
// ═════════════════════════════════════════════════════════════════════

void loop() {
    heartbeat.update();
    canBus.checkErrors();

    // ── CAN receive — drain queue ───────────────────────────────────
    uint32_t id;
    uint8_t  data[8];
    uint8_t  len;
    while (canBus.receive(id, data, len)) {
        canMessageReceived = true;

        switch (id) {

        // ── Speed → stepper needle ──────────────────────────────────
        case CAN_ID_BODY_SPEED: {
            double mph;
            memcpy(&mph, data, sizeof(double));
            stepperWheel.moveToMPH((int)mph);
            break;
        }

        // ── Gear → servo indicator disc ─────────────────────────────
        case CAN_ID_BODY_GEAR: {
            uint8_t gear = data[0];
            int angle;
            if (gear == GEAR_UNKNOWN) {
                angle = GEAR_ANGLE_UNKNOWN;
            } else if (gear <= GEAR_4) {
                angle = GEAR_ANGLES[gear];
            } else {
                angle = GEAR_ANGLE_UNKNOWN;
            }
            // Check reverse flag from body state
            if (lastBodyFlags & BODY_FLAG_REVERSE) {
                angle = GEAR_ANGLE_REVERSE;
            }
            gearServo.setAngle(angle);
            break;
        }

        // ── Odometer → future eInk display ──────────────────────────
        case CAN_ID_BODY_ODOMETER:
            // TODO: store for eInk update when driver is implemented
            break;

        // ── GPS speed → future discrepancy check ────────────────────
        case CAN_ID_GPS_SPEED:
            // TODO: compare with body speed for sensor validation
            break;

        // ── Ambient light → LED brightness ──────────────────────────
        case CAN_ID_GPS_AMBIENT_LIGHT:
            ledRing.setAmbientFromCategory(data[0]);
            break;

        // ── Body state → turn signal / hazard animations ────────────
        case CAN_ID_BODY_STATE:
            lastBodyFlags = data[0];
            break;

        // ── On-demand self-test ─────────────────────────────────────
        case CAN_ID_SELF_TEST: {
            uint8_t target = data[0];
            if (target == SELF_TEST_TARGET_ALL ||
                target == static_cast<uint8_t>(LOG_ROLE)) {
                runSelfTest();
            }
            break;
        }

        default:
            break;
        }
    }

    // ── Update all actuators ────────────────────────────────────────
    stepperWheel.update();
    gearServo.update();
    updateAnimations();
    ledRing.update();

    // ── CAN silence watchdog ────────────────────────────────────────
    if (!canMessageReceived && millis() > CAN_SILENCE_TIMEOUT_MS) {
        if (!canSilenceMode) {
            canSilenceMode = true;
            ledRing.startBluePulse();
            canLog.log(LogLevel::LOG_WARN, LogEvent::CAN_SILENCE);
            ESP_LOGW(TAG, "CAN silence — entering fault mode");
        }
    }
    if (canMessageReceived && canSilenceMode) {
        canSilenceMode = false;
        ledRing.stopBluePulse();
        canLog.log(LogLevel::LOG_INFO, LogEvent::BUS_RECOVERED);
        ESP_LOGI(TAG, "CAN traffic resumed");
    }
}
