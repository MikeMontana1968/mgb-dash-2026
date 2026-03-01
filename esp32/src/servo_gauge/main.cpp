/**
 * MGB Dash 2026 — Servo Gauge Main
 *
 * Shared entry point for FUEL, AMPS, and TEMP servo gauges.
 * Build-time constant GAUGE_ROLE selects behavior.
 */

#include <Arduino.h>
#include <cmath>
#include "esp_log.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LedRing.h"
#include "ServoGauge.h"
#include "LeafCan.h"
#include "can_ids.h"

static const char* TAG = GAUGE_ROLE_NAME;
static constexpr LogRole ROLE = LOG_ROLE;

CanBus canBus;
Heartbeat heartbeat;
CanLog canLog;
LedRing ledRing;
ServoGauge servo;
LeafCan leafCan;

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode = false;

// ── Gauge value state ──────────────────────────────────────────────
float gaugeValue = 0.0f;
unsigned long lastGaugeUpdateMs = 0;
static constexpr unsigned long GAUGE_STALE_MS = 2000;

// ── Turn signal / hazard holdoff ───────────────────────────────────
unsigned long lastLeftMs = 0;
unsigned long lastRightMs = 0;
unsigned long lastHazardMs = 0;
static constexpr unsigned long TURN_HOLDOFF_MS = 600;

enum AnimState { ANIM_NONE, ANIM_HAZARD, ANIM_LEFT, ANIM_RIGHT };
AnimState currentAnim = ANIM_NONE;

// ── Body state flags (from 0x710) ──────────────────────────────────
uint8_t lastBodyFlags = 0;

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

// ── Coordinated self-test ───────────────────────────────────────────
// Sweep needle 0→180→0 with synchronized rainbow LED ring animation.
// Total duration ~3.5 seconds.
void runSelfTest() {
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    ESP_LOGI(TAG, "Self-test starting...");

    const int degreesPerLed = 180 / LED_COUNT;  // 15° per LED for 12 LEDs

    // ── Phase 1: Sweep up (0→180) with rainbow fill ─────────────────
    // LEDs light up progressively as needle passes each position
    for (int a = 0; a <= 180; a += 2) {
        servo.writeDirect(a);

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

    // ── Phase 2: Hold at 180° — white flash ─────────────────────────
    ledRing.setAll(255, 255, 255);
    ledRing.show();
    delay(150);
    // Restore rainbow
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t r, g, b;
        wheelToRGB((i * 256) / LED_COUNT, r, g, b);
        ledRing.setPixel(i, r, g, b);
    }
    ledRing.show();
    delay(150);

    // ── Phase 3: Sweep down (180→0) — LEDs extinguish in reverse ────
    for (int a = 180; a >= 0; a -= 2) {
        servo.writeDirect(a);

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

    // ── Phase 4: Pass indicator — double green flash ────────────────
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

    servo.writeDirect(0);
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);
    ESP_LOGI(TAG, "Self-test complete.");
}

// ═════════════════════════════════════════════════════════════════════
// LED warning colors based on gauge value thresholds
// ═════════════════════════════════════════════════════════════════════
static void updateWarnings() {
    // Don't override turn signal / hazard animations
    if (currentAnim != ANIM_NONE) return;

    // Don't override blue pulse fault mode
    if (canSilenceMode) return;

    // Stale data warning (amber) — only after first value received
    if (lastGaugeUpdateMs > 0 && (millis() - lastGaugeUpdateMs) > GAUGE_STALE_MS) {
        ledRing.setWarning(255, 100, 0);
        return;
    }

    if (ROLE == LogRole::FUEL) {
        if (gaugeValue < 10.0f) {
            ledRing.setWarning(255, 0, 0);       // red — critically low SOC
        } else if (gaugeValue < 20.0f) {
            ledRing.setWarning(255, 180, 0);     // amber — low SOC
        } else {
            ledRing.clearWarning();
        }
    } else if (ROLE == LogRole::AMPS) {
        float absAmps = fabsf(gaugeValue);
        if (absAmps > 150.0f) {
            ledRing.setWarning(255, 0, 0);       // red — extreme current
        } else if (absAmps > 100.0f) {
            ledRing.setWarning(255, 180, 0);     // amber — high current
        } else {
            ledRing.clearWarning();
        }
    } else if (ROLE == LogRole::TEMP) {
        if (gaugeValue > 45.0f || gaugeValue < -5.0f) {
            ledRing.setWarning(255, 0, 0);       // red — extreme temp
        } else if (gaugeValue > 35.0f || gaugeValue < 0.0f) {
            ledRing.setWarning(255, 180, 0);     // amber — concerning temp
        } else {
            ledRing.clearWarning();
        }
    }
}

// ═════════════════════════════════════════════════════════════════════
// Turn signal / hazard animation from body controller flags (0x710)
// Uses holdoff timer to bridge relay blink gaps.
// ═════════════════════════════════════════════════════════════════════
static void updateAnimations() {
    unsigned long now = millis();

    // Update holdoff timestamps from latest body flags
    if (lastBodyFlags & BODY_FLAG_HAZARD)     lastHazardMs = now;
    if (lastBodyFlags & BODY_FLAG_LEFT_TURN)  lastLeftMs   = now;
    if (lastBodyFlags & BODY_FLAG_RIGHT_TURN) lastRightMs  = now;

    // Determine desired animation (hazard > left > right)
    bool hazardActive = lastHazardMs > 0 && (now - lastHazardMs) < TURN_HOLDOFF_MS;
    bool leftActive   = lastLeftMs   > 0 && (now - lastLeftMs)   < TURN_HOLDOFF_MS;
    bool rightActive  = lastRightMs  > 0 && (now - lastRightMs)  < TURN_HOLDOFF_MS;

    AnimState desired = ANIM_NONE;
    if (hazardActive)      desired = ANIM_HAZARD;
    else if (leftActive)   desired = ANIM_LEFT;
    else if (rightActive)  desired = ANIM_RIGHT;

    // Only change animation on state transition
    if (desired != currentAnim) {
        switch (desired) {
            case ANIM_HAZARD: ledRing.startHazard();            break;
            case ANIM_LEFT:   ledRing.startTurnSignal(true);    break;
            case ANIM_RIGHT:  ledRing.startTurnSignal(false);   break;
            case ANIM_NONE:   ledRing.stopAnimation();          break;
        }
        currentAnim = desired;
    }
}

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
    servo.init(PIN_SERVO);

    // ── Gauge-specific servo range and damping ────────────────────────
    if (ROLE == LogRole::FUEL) {
        servo.setRange(0.0f, 100.0f);      // SOC 0–100%
        servo.setSmoothing(0.8f);           // slow — SOC changes gradually
    } else if (ROLE == LogRole::AMPS) {
        servo.setRange(-100.0f, 200.0f);   // -100A regen to 200A discharge
        servo.setSmoothing(0.3f);           // snappy — current changes fast
    } else if (ROLE == LogRole::TEMP) {
        servo.setRange(-10.0f, 50.0f);     // -10°C to 50°C
        servo.setSmoothing(1.0f);          // slow — temp changes very gradually
    }

    // ── Self-test at startup ─────────────────────────────────────────
    runSelfTest();

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

void loop() {
    heartbeat.update();
    canBus.checkErrors();

    // ── CAN receive — drain queue ───────────────────────────────────
    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    while (canBus.receive(id, data, len)) {
        canMessageReceived = true;

        // ── On-demand self-test via CAN 0x730 ────────────────────────
        if (id == CAN_ID_SELF_TEST) {
            uint8_t target = data[0];
            if (target == SELF_TEST_TARGET_ALL ||
                target == static_cast<uint8_t>(LOG_ROLE)) {
                runSelfTest();
            }
        }

        // ── Gauge-specific Leaf CAN decode ───────────────────────────
        if (ROLE == LogRole::FUEL) {
            if (id == CAN_ID_LEAF_SOC_PRECISE) {
                // Primary: precise SOC from 0x55B
                gaugeValue = LeafCan::decodePreciseSOC(data);
                lastGaugeUpdateMs = millis();
            } else if (id == CAN_ID_LEAF_BATTERY_STATUS) {
                // Fallback: coarse SOC from 0x1DB if precise is stale
                if (millis() - lastGaugeUpdateMs > 1000) {
                    BatteryStatus bs = LeafCan::decodeBatteryStatus(data);
                    gaugeValue = bs.socPercent;
                    lastGaugeUpdateMs = millis();
                }
            }
        } else if (ROLE == LogRole::AMPS) {
            if (id == CAN_ID_LEAF_BATTERY_STATUS) {
                BatteryStatus bs = LeafCan::decodeBatteryStatus(data);
                gaugeValue = bs.currentA;
                lastGaugeUpdateMs = millis();
            }
        } else if (ROLE == LogRole::TEMP) {
            if (id == CAN_ID_LEAF_BATTERY_TEMP) {
                gaugeValue = (float)LeafCan::decodeBatteryTemp(data);
                lastGaugeUpdateMs = millis();
            }
        }

        // ── Common: body state flags (turn signals, hazards) ─────────
        if (id == CAN_ID_BODY_STATE) {
            lastBodyFlags = data[0];
        }

        // ── Common: ambient light level ──────────────────────────────
        if (id == CAN_ID_GPS_AMBIENT_LIGHT) {
            ledRing.setAmbientFromCategory(data[0]);
        }
    }

    // ── Update servo from gauge value ────────────────────────────────
    servo.setValue(gaugeValue);

    // ── Update LED ring warnings and animations ─────────────────────
    updateAnimations();
    updateWarnings();

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

    ledRing.update();
    servo.update();
}
