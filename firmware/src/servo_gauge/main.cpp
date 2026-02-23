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

void setup() {
    Serial.begin(115200);
    ESP_LOGI(TAG, "Servo gauge starting...");

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START);

    canBus.init(CAN_TX_PIN, CAN_RX_PIN, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(LED_DATA_PIN, LED_COUNT);
    servo.init(SERVO_PIN);

    // ── Self-test ───────────────────────────────────────────────────
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    ledRing.runSelfTestChase();
    servo.runSelfTestSweep();
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);

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
