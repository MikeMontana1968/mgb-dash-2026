#pragma once
/**
 * MGB Dash 2026 — Leaf AZE0 CAN Message Decode Constants
 *
 * Single source of truth: common/can_ids.json
 * Target: 2013 Leaf drivetrain + 2014 battery (AZE0)
 *
 * All byte offsets are 0-indexed. Multi-byte values are big-endian
 * unless noted otherwise.
 */

#include <cstdint>

// ═══════════════════════════════════════════════════════════════════════
// 0x1DA — Motor Status (LEAF_MOTOR_STATUS)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf1DA {
    constexpr uint32_t ID = 0x1DA;
    constexpr uint8_t  DLC = 8;

    // Motor RPM — bytes 1–2, big-endian, signed 16-bit
    constexpr uint8_t RPM_BYTE_HI   = 1;
    constexpr uint8_t RPM_BYTE_LO   = 2;
    // Raw value is signed RPM directly (factor=1, offset=0)

    // Available torque — bytes 3–4, upper 10 bits, big-endian
    constexpr uint8_t TORQUE_BYTE_HI = 3;
    constexpr uint8_t TORQUE_BYTE_LO = 4;
    constexpr uint8_t TORQUE_BITS    = 10;
    constexpr float   TORQUE_FACTOR  = 0.5f;
    constexpr float   TORQUE_OFFSET  = -400.0f;  // Nm

    // Fail-safe — byte 6, bits 2–3
    constexpr uint8_t FAILSAFE_BYTE = 6;
    constexpr uint8_t FAILSAFE_SHIFT = 2;
    constexpr uint8_t FAILSAFE_MASK  = 0x03;
}

// ═══════════════════════════════════════════════════════════════════════
// 0x1DB — Battery Status (LEAF_BATTERY_STATUS)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf1DB {
    constexpr uint32_t ID = 0x1DB;
    constexpr uint8_t  DLC = 8;

    // Battery voltage — bytes 0–1, upper 10 bits, big-endian
    constexpr uint8_t VOLTAGE_BYTE_HI = 0;
    constexpr uint8_t VOLTAGE_BYTE_LO = 1;
    constexpr uint8_t VOLTAGE_BITS    = 10;
    constexpr float   VOLTAGE_FACTOR  = 0.5f;  // V

    // Battery current — bytes 2–3, upper 11 bits, big-endian, signed
    // Positive = discharge, negative = charge/regen
    constexpr uint8_t CURRENT_BYTE_HI = 2;
    constexpr uint8_t CURRENT_BYTE_LO = 3;
    constexpr uint8_t CURRENT_BITS    = 11;
    constexpr float   CURRENT_FACTOR  = 0.5f;  // A

    // Usable SOC — byte 4
    constexpr uint8_t SOC_BYTE = 4;
    // Raw value is SOC percentage directly (0–100)
}

// ═══════════════════════════════════════════════════════════════════════
// 0x55A — Inverter/Motor Temperatures (LEAF_INVERTER_TEMPS)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf55A {
    constexpr uint32_t ID = 0x55A;
    constexpr uint8_t  DLC = 8;

    // All temps: raw / 2 = °C
    constexpr uint8_t MOTOR_TEMP_BYTE   = 0;
    constexpr uint8_t IGBT_TEMP_BYTE    = 1;
    constexpr uint8_t INVERTER_TEMP_BYTE = 2;
    constexpr float   TEMP_FACTOR       = 0.5f;  // raw * factor = °C
}

// ═══════════════════════════════════════════════════════════════════════
// 0x55B — Precise SOC (LEAF_SOC_PRECISE)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf55B {
    constexpr uint32_t ID = 0x55B;
    constexpr uint8_t  DLC = 8;

    // SOC — bytes 0–1, big-endian, unsigned 16-bit
    constexpr uint8_t SOC_BYTE_HI = 0;
    constexpr uint8_t SOC_BYTE_LO = 1;
    constexpr float   SOC_FACTOR  = 0.01f;  // raw * factor = %
}

// ═══════════════════════════════════════════════════════════════════════
// 0x5BC — Battery Health (LEAF_BATTERY_HEALTH)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf5BC {
    constexpr uint32_t ID = 0x5BC;
    constexpr uint8_t  DLC = 8;

    // GIDs — bytes 0–1, upper 10 bits, big-endian
    constexpr uint8_t GIDS_BYTE_HI = 0;
    constexpr uint8_t GIDS_BYTE_LO = 1;
    constexpr uint8_t GIDS_BITS    = 10;

    // SOH — byte 4, bits 1–7
    constexpr uint8_t SOH_BYTE  = 4;
    constexpr uint8_t SOH_SHIFT = 1;
    constexpr uint8_t SOH_MASK  = 0x7F;  // 7 bits
}

// ═══════════════════════════════════════════════════════════════════════
// 0x5C0 — Battery Temperature (LEAF_BATTERY_TEMP)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf5C0 {
    constexpr uint32_t ID = 0x5C0;
    constexpr uint8_t  DLC = 8;

    // Battery temp — byte 0, signed, offset -40
    constexpr uint8_t TEMP_BYTE   = 0;
    constexpr int8_t  TEMP_OFFSET = -40;  // raw + offset = °C
}

// ═══════════════════════════════════════════════════════════════════════
// 0x1DC — Charger Status (LEAF_CHARGER_STATUS)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf1DC {
    constexpr uint32_t ID = 0x1DC;
    constexpr uint8_t  DLC = 8;

    // Charge power — bytes 0–1, upper 10 bits, big-endian
    constexpr uint8_t POWER_BYTE_HI = 0;
    constexpr uint8_t POWER_BYTE_LO = 1;
    constexpr uint8_t POWER_BITS    = 10;
    constexpr float   POWER_FACTOR  = 0.25f;  // kW
}

// ═══════════════════════════════════════════════════════════════════════
// 0x390 — VCM Status (LEAF_VCM_STATUS)
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf390 {
    constexpr uint32_t ID = 0x390;
    constexpr uint8_t  DLC = 8;

    // Main relay — byte 4, bit 0
    constexpr uint8_t RELAY_BYTE = 4;
    constexpr uint8_t RELAY_BIT  = 0;
}

// ═══════════════════════════════════════════════════════════════════════
// 0x59E — AZE0 Generation Identifier
// ═══════════════════════════════════════════════════════════════════════
namespace Leaf59E {
    constexpr uint32_t ID = 0x59E;
    // Presence of this ID on the bus confirms AZE0 (2013–2017)
    // No specific payload decode needed — just check for presence
}
