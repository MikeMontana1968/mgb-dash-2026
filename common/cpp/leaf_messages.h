#pragma once
/**
 * MGB Dash 2026 — Leaf AZE0 CAN Message Decode Constants
 *
 * AUTO-GENERATED from common/can_ids.json — do not edit by hand.
 * Regenerate:  python python/tools/codegen.py
 *
 * All byte offsets are 0-indexed. Multi-byte values are big-endian
 * unless noted otherwise.
 */

#include <cstdint>

// ===================================================================
// 0x1DA — Motor RPM, torque, fail-safe status (LEAF_MOTOR_STATUS)
// ===================================================================
namespace Leaf1DA {
    constexpr uint32_t ID = 0x1DA;
    constexpr uint8_t  DLC = 8;

    // MotorRPM — bytes 1–2, 16 bits, big-endian
    constexpr uint8_t RPM_BYTE_HI = 1;
    constexpr uint8_t RPM_BYTE_LO = 2;

    // AvailableTorque — bytes 3–4, upper 10 bits, big-endian
    constexpr uint8_t TORQUE_BYTE_HI = 3;
    constexpr uint8_t TORQUE_BYTE_LO = 4;
    constexpr uint8_t TORQUE_BITS    = 10;
    constexpr float   TORQUE_FACTOR  = 0.5f;
    constexpr float   TORQUE_OFFSET  = -400.0f;

    // FailSafe — byte 6, bits 2–3
    constexpr uint8_t FAILSAFE_BYTE  = 6;
    constexpr uint8_t FAILSAFE_SHIFT = 2;
    constexpr uint8_t FAILSAFE_MASK  = 0x03;
}

// ===================================================================
// 0x1DB — Battery voltage, current, SOC (LEAF_BATTERY_STATUS)
// ===================================================================
namespace Leaf1DB {
    constexpr uint32_t ID = 0x1DB;
    constexpr uint8_t  DLC = 8;

    // BatteryVoltage — bytes 0–1, upper 10 bits, big-endian
    constexpr uint8_t VOLTAGE_BYTE_HI = 0;
    constexpr uint8_t VOLTAGE_BYTE_LO = 1;
    constexpr uint8_t VOLTAGE_BITS    = 10;
    constexpr float   VOLTAGE_FACTOR  = 0.5f;

    // BatteryCurrent — bytes 2–3, upper 11 bits, big-endian
    constexpr uint8_t CURRENT_BYTE_HI = 2;
    constexpr uint8_t CURRENT_BYTE_LO = 3;
    constexpr uint8_t CURRENT_BITS    = 11;
    constexpr float   CURRENT_FACTOR  = 0.5f;

    // SOC — byte 4
    constexpr uint8_t SOC_BYTE = 4;
}

// ===================================================================
// 0x1DC — Charger/OBC status and power (LEAF_CHARGER)
// ===================================================================
namespace Leaf1DC {
    constexpr uint32_t ID = 0x1DC;
    constexpr uint8_t  DLC = 8;

    // ChargePower — bytes 0–1, upper 10 bits, big-endian
    constexpr uint8_t POWER_BYTE_HI = 0;
    constexpr uint8_t POWER_BYTE_LO = 1;
    constexpr uint8_t POWER_BITS    = 10;
    constexpr float   POWER_FACTOR  = 0.25f;
}

// ===================================================================
// 0x390 — VCM operational status (LEAF_VCM)
// ===================================================================
namespace Leaf390 {
    constexpr uint32_t ID = 0x390;
    constexpr uint8_t  DLC = 8;

    // VCMMainRelay — byte 4, bit 0
    constexpr uint8_t RELAY_BYTE = 4;
    constexpr uint8_t RELAY_BIT  = 0;
}

// ===================================================================
// 0x55A — Motor and inverter temperatures (LEAF_INVERTER_TEMPS)
// ===================================================================
namespace Leaf55A {
    constexpr uint32_t ID = 0x55A;
    constexpr uint8_t  DLC = 8;

    // MotorTemperature — byte 0
    constexpr uint8_t MOTOR_TEMP_BYTE = 0;
    constexpr float   MOTOR_TEMP_FACTOR  = 0.5f;

    // IGBTTemperature — byte 1
    constexpr uint8_t IGBT_TEMP_BYTE = 1;
    constexpr float   IGBT_TEMP_FACTOR  = 0.5f;

    // InverterComBoardTemp — byte 2
    constexpr uint8_t INVERTER_TEMP_BYTE = 2;
    constexpr float   INVERTER_TEMP_FACTOR  = 0.5f;
}

// ===================================================================
// 0x55B — High-precision SOC (LEAF_SOC_PRECISE)
// ===================================================================
namespace Leaf55B {
    constexpr uint32_t ID = 0x55B;
    constexpr uint8_t  DLC = 8;

    // SOC_Precise — bytes 0–1, 16 bits, big-endian
    constexpr uint8_t SOC_BYTE_HI = 0;
    constexpr uint8_t SOC_BYTE_LO = 1;
    constexpr float   SOC_FACTOR  = 0.01f;
}

// ===================================================================
// 0x59E — Present only on AZE0 (2013–2017) Leaf — used for generation detection (LEAF_AZE0_ID)
// ===================================================================
namespace Leaf59E {
    constexpr uint32_t ID = 0x59E;
    // Presence of this ID on the bus confirms Present only on AZE0 (2013–2017) Leaf — used for generation detection
    // No specific payload decode needed — just check for presence
}

// ===================================================================
// 0x5BC — Battery capacity, SOH, GIDs (LEAF_BATTERY_HEALTH)
// ===================================================================
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
    constexpr uint8_t SOH_MASK  = 0x7F;
}

// ===================================================================
// 0x5C0 — Battery pack temperature (LEAF_BATTERY_TEMP)
// ===================================================================
namespace Leaf5C0 {
    constexpr uint32_t ID = 0x5C0;
    constexpr uint8_t  DLC = 8;

    // BatteryTemp — byte 0
    constexpr uint8_t TEMP_BYTE = 0;
    constexpr int8_t  TEMP_OFFSET = -40;
}
