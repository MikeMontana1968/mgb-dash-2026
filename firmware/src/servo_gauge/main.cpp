/**
 * MGB Dash 2026 — Servo Gauge Main
 *
 * Shared entry point for FUEL, AMPS, and TEMP servo gauges.
 * Build-time constant GAUGE_ROLE selects behavior.
 */

#include <Arduino.h>
#include "esp_log.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LedRing.h"
#include "ServoGauge.h"
#include "LeafCan.h"
#include "can_ids.h"

static const char* TAG = GAUGE_ROLE_NAME;

CanBus canBus;
Heartbeat heartbeat;
CanLog canLog;
LedRing ledRing;
ServoGauge servo;
LeafCan leafCan;

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode = false;

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

void setup() {
    Serial.begin(115200);
    ESP_LOGI(TAG, "Servo gauge starting...");

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START);

    canBus.init(CAN_TX_PIN, CAN_RX_PIN, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(LED_DATA_PIN, LED_COUNT);
    servo.init(SERVO_PIN);

    // ── Self-test at startup ─────────────────────────────────────────
    runSelfTest();

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

void loop() {
    heartbeat.update();

    // TODO: Read CAN messages relevant to this gauge role
    // TODO: Decode Leaf CAN data via leafCan
    // TODO: Map decoded value to servo angle
    // TODO: Update LED ring based on value thresholds and ambient light
    // TODO: Handle turn signal / hazard animation on LED ring

    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    if (canBus.receive(id, data, len)) {
        canMessageReceived = true;

        // ── On-demand self-test via CAN 0x730 ────────────────────────
        if (id == CAN_ID_SELF_TEST) {
            uint8_t target = data[0];
            if (target == SELF_TEST_TARGET_ALL ||
                target == static_cast<uint8_t>(LOG_ROLE)) {
                runSelfTest();
            }
        }

        // TODO: Dispatch to appropriate handler based on GAUGE_ROLE
    }

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
