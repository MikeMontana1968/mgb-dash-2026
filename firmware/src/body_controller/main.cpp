/**
 * MGB Dash 2026 — Body Controller Main
 *
 * Reads vehicle sensor states, hall sensor for speed/odometer,
 * estimates gear, broadcasts on CAN, serves BLE.
 */

#include <Arduino.h>
#include "CanBus.h"
#include "Heartbeat.h"
#include "LeafCan.h"
#include "can_ids.h"
#include <Preferences.h>

CanBus canBus;
Heartbeat heartbeat;
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

void setup() {
    Serial.begin(115200);
    Serial.println("[BODY] Body controller starting...");

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
    Serial.printf("[BODY] Odometer loaded: %.1f miles\n", odometerMiles);

    // TODO: Init BLE peripheral

    Serial.println("[BODY] Init complete.");
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
        // TODO: Decode Leaf motor RPM from 0x1DA for gear estimation
    }

    delay(10);  // TODO: Replace with proper timing
}
