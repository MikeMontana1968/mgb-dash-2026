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

static const char* TAG = GAUGE_ROLE_NAME;

CanBus canBus;
Heartbeat heartbeat;
CanLog canLog;
LeafCan leafCan;
Preferences prefs;

// ── Hall sensor state ───────────────────────────────────────────────
volatile uint32_t hallPulseCount = 0;
volatile unsigned long lastHallPulseUs = 0;

void IRAM_ATTR hallISR() {
    hallPulseCount++;
    lastHallPulseUs = micros();
}

// ── Odometer ────────────────────────────────────────────────────────
double odometerMiles = 0.0;
double odometerSinceLastPersist = 0.0;

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode = false;

void setup() {
    Serial.begin(115200);
    ESP_LOGI(TAG, "Body controller starting...");

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START);

    canBus.init(CAN_TX_PIN, CAN_RX_PIN, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);

    // Digital inputs
    pinMode(KEY_ON_PIN, INPUT);
    pinMode(BRAKE_PIN, INPUT);
    pinMode(REGEN_PIN, INPUT);
    pinMode(FAN_PIN, INPUT);
    pinMode(REVERSE_PIN, INPUT);
    pinMode(LEFT_TURN_PIN, INPUT);
    pinMode(RIGHT_TURN_PIN, INPUT);

    // Hall sensor (interrupt-driven)
    pinMode(HALL_SENSOR_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(HALL_SENSOR_PIN), hallISR, FALLING);

    // Load persisted odometer from NVS
    prefs.begin("odo", true);  // read-only
    odometerMiles = prefs.getDouble("miles", 0.0);
    prefs.end();
    ESP_LOGI(TAG, "Odometer loaded: %.1f miles", odometerMiles);

    // TODO: Init BLE peripheral

    // ── Self-test (log only, no visual hardware on body controller) ──
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

void loop() {
    heartbeat.update();

    // TODO: Read digital inputs, apply hazard detection state machine
    // TODO: Broadcast body state flags on 0x710 at 10 Hz
    // TODO: Compute speed from hall sensor pulse timing
    // TODO: Broadcast speed on 0x711
    // TODO: Read motor RPM from Leaf CAN (0x1DA), compute gear estimate
    // TODO: Broadcast gear on 0x712
    // TODO: Update odometer, persist to NVS every ODO_PERSIST_MILES
    // TODO: Broadcast odometer on 0x713
    // TODO: Update BLE characteristics

    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    if (canBus.receive(id, data, len)) {
        canMessageReceived = true;
        // TODO: Decode Leaf motor RPM from 0x1DA for gear estimation
    }

    // ── CAN silence watchdog (serial + log only, no LED ring) ───────
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

    delay(10);  // TODO: Replace with proper timing
}
