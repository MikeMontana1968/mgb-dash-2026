/**
 * MGB Dash 2026 — Speedometer Main
 *
 * Stepper motor slot-machine display + servo gear indicator
 * + eInk odometer + WS2812B LED ring.
 */

#include <Arduino.h>
#include "esp_log.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LedRing.h"
#include "can_ids.h"

static const char* TAG = GAUGE_ROLE_NAME;

CanBus canBus;
Heartbeat heartbeat;
CanLog canLog;
LedRing ledRing;

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode = false;

void setup() {
    Serial.begin(115200);
    ESP_LOGI(TAG, "Speedometer starting...");

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START);

    canBus.init(PIN_CAN_TX, PIN_CAN_RX, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(PIN_LED_DATA, LED_COUNT);

    // Stepper home sensor (optical endstop, active-low)
    pinMode(PIN_STEPPER_HOME, INPUT_PULLUP);

    // TODO: Init stepper motor driver (28BYJ-48 + ULN2003)
    // TODO: Home stepper — rotate until PIN_STEPPER_HOME goes LOW, then zero position
    // TODO: Init servo for gear indicator disc
    // TODO: Init eInk display (SPI, tri-color 1.54" 200x200)

    // ── Self-test (LED ring only; stepper/eInk are future TODOs) ────
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    ledRing.runSelfTestChase();
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

void loop() {
    heartbeat.update();

    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    if (canBus.receive(id, data, len)) {
        canMessageReceived = true;
        // TODO: Handle BODY_SPEED (0x711) → stepper motor position
        // TODO: Handle GPS_SPEED (0x720) → speed discrepancy check
        // TODO: Handle BODY_GEAR (0x712) → servo gear indicator
        // TODO: Handle BODY_ODOMETER (0x713) → eInk update
        // TODO: Handle GPS_AMBIENT_LIGHT (0x726) → LED ring brightness
        // TODO: Handle BODY_STATE (0x710) → turn signal animation
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
}
