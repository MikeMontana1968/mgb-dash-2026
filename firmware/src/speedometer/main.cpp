/**
 * MGB Dash 2026 — Speedometer Main
 *
 * Stepper motor slot-machine display + servo gear indicator
 * + eInk odometer + WS2812B LED ring.
 */

#include <Arduino.h>
#include "CanBus.h"
#include "Heartbeat.h"
#include "LedRing.h"
#include "can_ids.h"

CanBus canBus;
Heartbeat heartbeat;
LedRing ledRing;

void setup() {
    Serial.begin(115200);
    Serial.println("[SPEED] Speedometer starting...");

    canBus.init(CAN_TX_PIN, CAN_RX_PIN, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(LED_DATA_PIN, LED_COUNT);

    // TODO: Init stepper motor driver
    // TODO: Init servo for gear indicator disc
    // TODO: Init eInk display (SPI, tri-color 1.54" 200x200)

    Serial.println("[SPEED] Init complete.");
}

void loop() {
    heartbeat.update();

    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    if (canBus.receive(id, data, len)) {
        // TODO: Handle BODY_SPEED (0x711) → stepper motor position
        // TODO: Handle GPS_SPEED (0x720) → speed discrepancy check
        // TODO: Handle BODY_GEAR (0x712) → servo gear indicator
        // TODO: Handle BODY_ODOMETER (0x713) → eInk update
        // TODO: Handle GPS_AMBIENT_LIGHT (0x726) → LED ring brightness
        // TODO: Handle BODY_STATE (0x710) → turn signal animation
    }

    delay(10);  // TODO: Replace with proper timing
}
