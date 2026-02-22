/**
 * MGB Dash 2026 — Servo Gauge Main
 *
 * Shared entry point for FUEL, AMPS, and TEMP servo gauges.
 * Build-time constant GAUGE_ROLE selects behavior.
 */

#include <Arduino.h>
#include "CanBus.h"
#include "Heartbeat.h"
#include "LedRing.h"
#include "ServoGauge.h"
#include "LeafCan.h"
#include "can_ids.h"

CanBus canBus;
Heartbeat heartbeat;
LedRing ledRing;
ServoGauge servo;
LeafCan leafCan;

void setup() {
    Serial.begin(115200);
    Serial.printf("[%s] Servo gauge starting...\n", GAUGE_ROLE_NAME);

    canBus.init(CAN_TX_PIN, CAN_RX_PIN, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(LED_DATA_PIN, LED_COUNT);
    servo.init(SERVO_PIN);

    Serial.printf("[%s] Init complete.\n", GAUGE_ROLE_NAME);
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
        // TODO: Dispatch to appropriate handler based on GAUGE_ROLE
    }

    delay(10);  // TODO: Replace with proper timing
}
