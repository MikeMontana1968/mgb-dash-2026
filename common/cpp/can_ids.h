#pragma once
/**
 * MGB Dash 2026 — Custom CAN Arbitration IDs
 *
 * Single source of truth: common/can_ids.json
 * This file is a manually-maintained C++ mirror.
 */

#include <cstdint>

// ── Custom CAN ID range ──────────────────────────────────────────────
constexpr uint32_t CAN_CUSTOM_ID_MIN = 0x700;
constexpr uint32_t CAN_CUSTOM_ID_MAX = 0x73F;

// ── Heartbeat (all modules) ─────────────────────────────────────────
constexpr uint32_t CAN_ID_HEARTBEAT = 0x700;
constexpr uint8_t  HEARTBEAT_LEN    = 8;
constexpr uint16_t HEARTBEAT_INTERVAL_MS = 1000;

// Heartbeat role names — 5 bytes, space-padded
constexpr char ROLE_FUEL[6]  = "FUEL ";
constexpr char ROLE_AMPS[6]  = "AMPS ";
constexpr char ROLE_TEMP[6]  = "TEMP ";
constexpr char ROLE_SPEED[6] = "SPEED";
constexpr char ROLE_BODY[6]  = "BODY ";
constexpr char ROLE_DASH[6]  = "DASH ";
constexpr char ROLE_GPS[6]   = "GPS  ";

// Heartbeat payload byte offsets
constexpr uint8_t HB_ROLE_OFFSET    = 0;  // bytes 0–4: role name
constexpr uint8_t HB_ROLE_LEN       = 5;
constexpr uint8_t HB_UPTIME_OFFSET  = 5;  // byte 5: rolling counter 0–255
constexpr uint8_t HB_ERROR_OFFSET   = 6;  // byte 6: error flags bitfield
constexpr uint8_t HB_RESERVED_OFFSET = 7; // byte 7: reserved (0x00)

// ── Body Controller ─────────────────────────────────────────────────
constexpr uint32_t CAN_ID_BODY_STATE    = 0x710;  // Vehicle state bit flags, 10 Hz
constexpr uint32_t CAN_ID_BODY_SPEED    = 0x711;  // Speed (64-bit double, mph)
constexpr uint32_t CAN_ID_BODY_GEAR     = 0x712;  // Estimated gear
constexpr uint32_t CAN_ID_BODY_ODOMETER = 0x713;  // Odometer (uint32, miles)

// Body state bit flags (byte 0 of 0x710 payload)
constexpr uint8_t BODY_FLAG_KEY_ON       = (1 << 0);
constexpr uint8_t BODY_FLAG_BRAKE        = (1 << 1);
constexpr uint8_t BODY_FLAG_REGEN        = (1 << 2);
constexpr uint8_t BODY_FLAG_FAN          = (1 << 3);
constexpr uint8_t BODY_FLAG_REVERSE      = (1 << 4);
constexpr uint8_t BODY_FLAG_LEFT_TURN    = (1 << 5);
constexpr uint8_t BODY_FLAG_RIGHT_TURN   = (1 << 6);
constexpr uint8_t BODY_FLAG_HAZARD       = (1 << 7);

// Gear values (byte 0 of 0x712 payload)
constexpr uint8_t GEAR_NEUTRAL = 0;
constexpr uint8_t GEAR_1       = 1;
constexpr uint8_t GEAR_2       = 2;
constexpr uint8_t GEAR_3       = 3;
constexpr uint8_t GEAR_4       = 4;
constexpr uint8_t GEAR_UNKNOWN = 0xFF;

// ── Self-Test Command ──────────────────────────────────────────────
constexpr uint32_t CAN_ID_SELF_TEST      = 0x730;  // On-demand self-test trigger
constexpr uint8_t  SELF_TEST_TARGET_ALL  = 0xFF;   // byte 0 = 0xFF → all modules

// ── Logging ───────────────────────────────────────────────────────
constexpr uint32_t CAN_ID_LOG            = 0x731;  // Structured log event
constexpr uint32_t CAN_ID_LOG_TEXT       = 0x732;  // Log text continuation (up to 7 frames)
constexpr uint8_t  LOG_DLC              = 8;       // LOG frame is always 8 bytes
constexpr uint8_t  LOG_TEXT_DLC         = 8;       // LOG_TEXT frame is always 8 bytes
constexpr uint8_t  LOG_TEXT_MAX_FRAMES  = 7;       // Max text continuation frames
constexpr uint8_t  LOG_TEXT_CHARS_PER_FRAME = 7;   // 7 ASCII chars per text frame

// ── GPS Module ──────────────────────────────────────────────────────
constexpr uint32_t CAN_ID_GPS_SPEED         = 0x720;  // Speed (64-bit double, mph)
constexpr uint32_t CAN_ID_GPS_TIME          = 0x721;  // Seconds since midnight UTC
constexpr uint32_t CAN_ID_GPS_DATE          = 0x722;  // Days since 2000-01-01
constexpr uint32_t CAN_ID_GPS_LATITUDE      = 0x723;  // Decimal degrees
constexpr uint32_t CAN_ID_GPS_LONGITUDE     = 0x724;  // Decimal degrees
constexpr uint32_t CAN_ID_GPS_ELEVATION     = 0x725;  // Meters above sea level
constexpr uint32_t CAN_ID_GPS_AMBIENT_LIGHT = 0x726;  // 0–3 category
constexpr uint32_t CAN_ID_GPS_UTC_OFFSET    = 0x727;  // int16 signed, UTC offset in minutes

// Ambient light categories (byte 0 of 0x726 payload)
constexpr uint8_t AMBIENT_DAYLIGHT       = 0;
constexpr uint8_t AMBIENT_EARLY_TWILIGHT = 1;
constexpr uint8_t AMBIENT_LATE_TWILIGHT  = 2;
constexpr uint8_t AMBIENT_DARKNESS       = 3;

// ── Resolve EV Controller ───────────────────────────────────────────
constexpr uint32_t CAN_ID_RESOLVE_DISPLAY = 0x539;

// ── Leaf EV-CAN IDs (AZE0, 2013–2017) ──────────────────────────────
constexpr uint32_t CAN_ID_LEAF_MOTOR_STATUS   = 0x1DA;
constexpr uint32_t CAN_ID_LEAF_BATTERY_STATUS = 0x1DB;
constexpr uint32_t CAN_ID_LEAF_CHARGER        = 0x1DC;
constexpr uint32_t CAN_ID_LEAF_VCM            = 0x390;
constexpr uint32_t CAN_ID_LEAF_INVERTER_TEMPS = 0x55A;
constexpr uint32_t CAN_ID_LEAF_SOC_PRECISE    = 0x55B;
constexpr uint32_t CAN_ID_LEAF_BATTERY_HEALTH = 0x5BC;
constexpr uint32_t CAN_ID_LEAF_BATTERY_TEMP   = 0x5C0;
constexpr uint32_t CAN_ID_LEAF_AZE0_ID        = 0x59E;

// ── CAN bus configuration ───────────────────────────────────────────
constexpr uint32_t CAN_BUS_SPEED = 500000;  // 500 kbps
constexpr uint32_t CAN_SILENCE_TIMEOUT_MS = 5000;  // default 5 seconds
