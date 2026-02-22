#pragma once
/**
 * MGB Dash 2026 — Leaf CAN Message Decoder Library
 *
 * Wraps common/cpp/leaf_messages.h decode constants into
 * convenient functions for ESP32 firmware.
 */

#include <Arduino.h>
#include "leaf_messages.h"
#include "resolve_messages.h"

struct MotorStatus {
    int16_t rpm;
    float availableTorqueNm;
    uint8_t failsafe;
};

struct BatteryStatus {
    float voltageV;
    float currentA;   // positive = discharge
    uint8_t socPercent;
};

struct InverterTemps {
    float motorTempC;
    float igbtTempC;
    float inverterTempC;
};

struct BatteryHealth {
    uint16_t gids;
    uint8_t sohPercent;
};

struct ResolveDisplay {
    uint8_t gear;
    bool ignitionOn;
    bool systemOn;
    bool displayMaxCharge;
    uint8_t regenStrength;
    uint8_t socPercent;
};

class LeafCan {
public:
    /** Decode 0x1DA — Motor Status */
    static MotorStatus decodeMotorStatus(const uint8_t* data);

    /** Decode 0x1DB — Battery Status */
    static BatteryStatus decodeBatteryStatus(const uint8_t* data);

    /** Decode 0x55A — Inverter/Motor Temperatures */
    static InverterTemps decodeInverterTemps(const uint8_t* data);

    /** Decode 0x55B — Precise SOC (returns %) */
    static float decodePreciseSOC(const uint8_t* data);

    /** Decode 0x5BC — Battery Health */
    static BatteryHealth decodeBatteryHealth(const uint8_t* data);

    /** Decode 0x5C0 — Battery Temperature (returns °C) */
    static int8_t decodeBatteryTemp(const uint8_t* data);

    /** Decode 0x1DC — Charger power (returns kW) */
    static float decodeChargerPower(const uint8_t* data);

    /** Decode 0x390 — VCM main relay state */
    static bool decodeMainRelay(const uint8_t* data);

    /** Decode 0x539 — Resolve EV Controller display message */
    static ResolveDisplay decodeResolveDisplay(const uint8_t* data);
};
