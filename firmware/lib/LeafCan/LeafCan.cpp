/**
 * MGB Dash 2026 — Leaf CAN Decoder Implementation
 */

#include "LeafCan.h"

MotorStatus LeafCan::decodeMotorStatus(const uint8_t* data) {
    MotorStatus s;
    s.rpm = (int16_t)((data[Leaf1DA::RPM_BYTE_HI] << 8) | data[Leaf1DA::RPM_BYTE_LO]);

    uint16_t torqueRaw = ((data[Leaf1DA::TORQUE_BYTE_HI] << 8) | data[Leaf1DA::TORQUE_BYTE_LO]) >> (16 - Leaf1DA::TORQUE_BITS);
    s.availableTorqueNm = torqueRaw * Leaf1DA::TORQUE_FACTOR + Leaf1DA::TORQUE_OFFSET;

    s.failsafe = (data[Leaf1DA::FAILSAFE_BYTE] >> Leaf1DA::FAILSAFE_SHIFT) & Leaf1DA::FAILSAFE_MASK;
    return s;
}

BatteryStatus LeafCan::decodeBatteryStatus(const uint8_t* data) {
    BatteryStatus s;

    uint16_t voltRaw = ((data[Leaf1DB::VOLTAGE_BYTE_HI] << 8) | data[Leaf1DB::VOLTAGE_BYTE_LO]) >> (16 - Leaf1DB::VOLTAGE_BITS);
    s.voltageV = voltRaw * Leaf1DB::VOLTAGE_FACTOR;

    uint16_t currRaw = ((data[Leaf1DB::CURRENT_BYTE_HI] << 8) | data[Leaf1DB::CURRENT_BYTE_LO]) >> (16 - Leaf1DB::CURRENT_BITS);
    // Sign-extend 11-bit value
    if (currRaw & (1 << (Leaf1DB::CURRENT_BITS - 1))) {
        currRaw |= 0xF800;  // extend sign for 16-bit
    }
    s.currentA = (int16_t)currRaw * Leaf1DB::CURRENT_FACTOR;

    s.socPercent = data[Leaf1DB::SOC_BYTE];
    return s;
}

InverterTemps LeafCan::decodeInverterTemps(const uint8_t* data) {
    InverterTemps t;
    t.motorTempC    = data[Leaf55A::MOTOR_TEMP_BYTE]    * Leaf55A::TEMP_FACTOR;
    t.igbtTempC     = data[Leaf55A::IGBT_TEMP_BYTE]     * Leaf55A::TEMP_FACTOR;
    t.inverterTempC = data[Leaf55A::INVERTER_TEMP_BYTE]  * Leaf55A::TEMP_FACTOR;
    return t;
}

float LeafCan::decodePreciseSOC(const uint8_t* data) {
    uint16_t raw = (data[Leaf55B::SOC_BYTE_HI] << 8) | data[Leaf55B::SOC_BYTE_LO];
    return raw * Leaf55B::SOC_FACTOR;
}

BatteryHealth LeafCan::decodeBatteryHealth(const uint8_t* data) {
    BatteryHealth h;
    h.gids = ((data[Leaf5BC::GIDS_BYTE_HI] << 8) | data[Leaf5BC::GIDS_BYTE_LO]) >> (16 - Leaf5BC::GIDS_BITS);
    h.sohPercent = (data[Leaf5BC::SOH_BYTE] >> Leaf5BC::SOH_SHIFT) & Leaf5BC::SOH_MASK;
    return h;
}

int8_t LeafCan::decodeBatteryTemp(const uint8_t* data) {
    return (int8_t)data[Leaf5C0::TEMP_BYTE] + Leaf5C0::TEMP_OFFSET;
}

float LeafCan::decodeChargerPower(const uint8_t* data) {
    uint16_t raw = ((data[Leaf1DC::POWER_BYTE_HI] << 8) | data[Leaf1DC::POWER_BYTE_LO]) >> (16 - Leaf1DC::POWER_BITS);
    return raw * Leaf1DC::POWER_FACTOR;
}

bool LeafCan::decodeMainRelay(const uint8_t* data) {
    return (data[Leaf390::RELAY_BYTE] >> Leaf390::RELAY_BIT) & 0x01;
}

ResolveDisplay LeafCan::decodeResolveDisplay(const uint8_t* data) {
    ResolveDisplay r;
    r.gear           = data[Resolve539::GEAR_BYTE] & Resolve539::GEAR_MASK;
    r.ignitionOn     = (data[0] >> Resolve539::IGNITION_ON_BIT) & 1;
    r.systemOn       = (data[0] >> Resolve539::SYSTEM_ON_BIT) & 1;
    r.displayMaxCharge = (data[0] >> Resolve539::DISPLAY_MAX_CHARGE_BIT) & 1;
    r.regenStrength  = data[Resolve539::REGEN_BYTE];
    r.socPercent     = data[Resolve539::SOC_BYTE];
    return r;
}
