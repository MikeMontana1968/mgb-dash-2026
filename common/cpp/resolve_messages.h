#pragma once
/**
 * MGB Dash 2026 — Resolve EV Controller CAN Message Decode Constants
 *
 * AUTO-GENERATED from common/can_ids.json — do not edit by hand.
 * Regenerate:  python python/tools/codegen.py
 *
 * All byte offsets are 0-indexed. Multi-byte values are big-endian
 * unless noted otherwise.
 */

#include <cstdint>

// ===================================================================
// 0x539 — Resolve EV Controller display message (RESOLVE_DISPLAY)
// ===================================================================
namespace Resolve539 {
    constexpr uint32_t ID = 0x539;
    constexpr uint8_t  DLC = 8;

    // Gear — byte 0
    constexpr uint8_t GEAR_BYTE  = 0;
    constexpr uint8_t GEAR_MASK  = 0x0F;

    // IgnitionOn — byte 0, bit 4
    constexpr uint8_t IGNITION_ON_BYTE = 0;
    constexpr uint8_t IGNITION_ON_BIT  = 4;

    // SystemOn — byte 0, bit 5
    constexpr uint8_t SYSTEM_ON_BYTE = 0;
    constexpr uint8_t SYSTEM_ON_BIT  = 5;

    // DisplayMaxChargeOn — byte 0, bit 6
    constexpr uint8_t DISPLAY_MAX_CHARGE_BYTE = 0;
    constexpr uint8_t DISPLAY_MAX_CHARGE_BIT  = 6;

    // RegenStrength — byte 1
    constexpr uint8_t REGEN_BYTE = 1;

    // SOCforDisplay — byte 2
    constexpr uint8_t SOC_BYTE = 2;
}
