#pragma once
/**
 * MGB Dash 2026 — Resolve EV Controller CAN Message Decode Constants
 *
 * Single source of truth: common/can_ids.json
 * Resolve EV Controller broadcasts 0x539 with display info.
 */

#include <cstdint>

// ═══════════════════════════════════════════════════════════════════════
// 0x539 — Resolve Display Message (RESOLVE_DISPLAY_MSG)
// ═══════════════════════════════════════════════════════════════════════
namespace Resolve539 {
    constexpr uint32_t ID = 0x539;

    // Gear — byte 0, bits 0–3 (lower nibble)
    constexpr uint8_t GEAR_BYTE  = 0;
    constexpr uint8_t GEAR_MASK  = 0x0F;

    // Flags — byte 0, upper nibble
    constexpr uint8_t IGNITION_ON_BIT       = 4;  // byte 0, bit 4
    constexpr uint8_t SYSTEM_ON_BIT         = 5;  // byte 0, bit 5
    constexpr uint8_t DISPLAY_MAX_CHARGE_BIT = 6; // byte 0, bit 6

    // Regen strength — byte 1
    constexpr uint8_t REGEN_BYTE = 1;

    // SOC for display — byte 2 (0–100%)
    constexpr uint8_t SOC_BYTE = 2;
}
