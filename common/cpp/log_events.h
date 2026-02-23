#pragma once
/**
 * MGB Dash 2026 — Structured Log Events
 *
 * Enums and helpers for the CAN log system (0x731 LOG, 0x732 LOG_TEXT).
 * Used by firmware (CanLog lib) and referenced in Python (can_log.py).
 *
 * LogLevel values are prefixed LOG_ to avoid Arduino DEBUG macro collision.
 */

#include <cstdint>

// ── Log Level (4 bits) ──────────────────────────────────────────────
enum class LogLevel : uint8_t {
    LOG_DEBUG    = 0,
    LOG_INFO     = 1,
    LOG_WARN     = 2,
    LOG_ERROR    = 3,
    LOG_CRITICAL = 4,
};

// ── Module Role (4 bits) — matches heartbeat roles ──────────────────
enum class LogRole : uint8_t {
    FUEL  = 0,
    AMPS  = 1,
    TEMP  = 2,
    SPEED = 3,
    BODY  = 4,
    DASH  = 5,
    GPS   = 6,
};

// ── Event Codes (uint8) ─────────────────────────────────────────────
enum class LogEvent : uint8_t {
    // Boot / Init (0x00–0x0F)
    BOOT_START       = 0x00,
    BOOT_COMPLETE    = 0x01,
    CAN_INIT_OK      = 0x02,
    CAN_INIT_FAIL    = 0x03,
    WIFI_OK          = 0x04,
    WIFI_FAIL        = 0x05,
    BLE_OK           = 0x06,
    BLE_FAIL         = 0x07,

    // CAN Health (0x10–0x1F)
    BUS_ERROR        = 0x10,
    BUS_OFF          = 0x11,
    BUS_RECOVERED    = 0x12,
    TX_FAIL          = 0x13,
    RX_OVERFLOW      = 0x14,

    // Self-Test (0x20–0x2F)
    SELF_TEST_START  = 0x20,
    SELF_TEST_PASS   = 0x21,
    SELF_TEST_FAIL   = 0x22,

    // Sensor / Gauge (0x30–0x3F)
    SENSOR_OUT_OF_RANGE = 0x30,
    SENSOR_TIMEOUT      = 0x31,
    SERVO_LIMIT         = 0x32,
    SERVO_STALL         = 0x33,
    STEPPER_HOME_OK     = 0x34,
    STEPPER_HOME_FAIL   = 0x35,

    // Comms (0x40–0x4F)
    HEARTBEAT_TIMEOUT  = 0x40,
    HEARTBEAT_RESUMED  = 0x41,
    BLE_CONNECT        = 0x42,
    BLE_DISCONNECT     = 0x43,
    GPS_FIX_ACQUIRED   = 0x44,
    GPS_FIX_LOST       = 0x45,
    CAN_SILENCE        = 0x46,

    // Power (0x50–0x5F)
    KEY_ON             = 0x50,
    KEY_OFF            = 0x51,
    LOW_VOLTAGE        = 0x52,
    OVERTEMP           = 0x53,

    // Display (0x60–0x6F)
    DISPLAY_INIT_OK    = 0x60,
    DISPLAY_INIT_FAIL  = 0x61,
    EINK_REFRESH       = 0x62,
    EINK_FAIL          = 0x63,

    // Generic (0xF0–0xFF)
    GENERIC_INFO       = 0xF0,
    GENERIC_WARN       = 0xF1,
    GENERIC_ERROR      = 0xF2,
    WATCHDOG_RESET     = 0xFD,
    ASSERT_FAILED      = 0xFE,
    UNKNOWN            = 0xFF,
};

// ── Inline Helpers ──────────────────────────────────────────────────

/** Pack role (high nibble) and level (low nibble) into byte 0. */
inline uint8_t packRoleLevel(LogRole role, LogLevel level) {
    return (static_cast<uint8_t>(role) << 4) | (static_cast<uint8_t>(level) & 0x0F);
}

/** Unpack role from byte 0. */
inline LogRole unpackRole(uint8_t byte0) {
    return static_cast<LogRole>(byte0 >> 4);
}

/** Unpack level from byte 0. */
inline LogLevel unpackLevel(uint8_t byte0) {
    return static_cast<LogLevel>(byte0 & 0x0F);
}

/** Human-readable level name. */
inline const char* levelName(LogLevel level) {
    switch (level) {
        case LogLevel::LOG_DEBUG:    return "DEBUG";
        case LogLevel::LOG_INFO:     return "INFO";
        case LogLevel::LOG_WARN:     return "WARN";
        case LogLevel::LOG_ERROR:    return "ERROR";
        case LogLevel::LOG_CRITICAL: return "CRITICAL";
        default:                     return "?";
    }
}

/** Human-readable role name. */
inline const char* roleName(LogRole role) {
    switch (role) {
        case LogRole::FUEL:  return "FUEL";
        case LogRole::AMPS:  return "AMPS";
        case LogRole::TEMP:  return "TEMP";
        case LogRole::SPEED: return "SPEED";
        case LogRole::BODY:  return "BODY";
        case LogRole::DASH:  return "DASH";
        case LogRole::GPS:   return "GPS";
        default:             return "?";
    }
}

/** Human-readable event name. */
inline const char* eventName(LogEvent event) {
    switch (event) {
        case LogEvent::BOOT_START:         return "BOOT_START";
        case LogEvent::BOOT_COMPLETE:      return "BOOT_COMPLETE";
        case LogEvent::CAN_INIT_OK:        return "CAN_INIT_OK";
        case LogEvent::CAN_INIT_FAIL:      return "CAN_INIT_FAIL";
        case LogEvent::WIFI_OK:            return "WIFI_OK";
        case LogEvent::WIFI_FAIL:          return "WIFI_FAIL";
        case LogEvent::BLE_OK:             return "BLE_OK";
        case LogEvent::BLE_FAIL:           return "BLE_FAIL";
        case LogEvent::BUS_ERROR:          return "BUS_ERROR";
        case LogEvent::BUS_OFF:            return "BUS_OFF";
        case LogEvent::BUS_RECOVERED:      return "BUS_RECOVERED";
        case LogEvent::TX_FAIL:            return "TX_FAIL";
        case LogEvent::RX_OVERFLOW:        return "RX_OVERFLOW";
        case LogEvent::SELF_TEST_START:    return "SELF_TEST_START";
        case LogEvent::SELF_TEST_PASS:     return "SELF_TEST_PASS";
        case LogEvent::SELF_TEST_FAIL:     return "SELF_TEST_FAIL";
        case LogEvent::SENSOR_OUT_OF_RANGE:return "SENSOR_OUT_OF_RANGE";
        case LogEvent::SENSOR_TIMEOUT:     return "SENSOR_TIMEOUT";
        case LogEvent::SERVO_LIMIT:        return "SERVO_LIMIT";
        case LogEvent::SERVO_STALL:        return "SERVO_STALL";
        case LogEvent::STEPPER_HOME_OK:    return "STEPPER_HOME_OK";
        case LogEvent::STEPPER_HOME_FAIL:  return "STEPPER_HOME_FAIL";
        case LogEvent::HEARTBEAT_TIMEOUT:  return "HEARTBEAT_TIMEOUT";
        case LogEvent::HEARTBEAT_RESUMED:  return "HEARTBEAT_RESUMED";
        case LogEvent::BLE_CONNECT:        return "BLE_CONNECT";
        case LogEvent::BLE_DISCONNECT:     return "BLE_DISCONNECT";
        case LogEvent::GPS_FIX_ACQUIRED:   return "GPS_FIX_ACQUIRED";
        case LogEvent::GPS_FIX_LOST:       return "GPS_FIX_LOST";
        case LogEvent::CAN_SILENCE:        return "CAN_SILENCE";
        case LogEvent::KEY_ON:             return "KEY_ON";
        case LogEvent::KEY_OFF:            return "KEY_OFF";
        case LogEvent::LOW_VOLTAGE:        return "LOW_VOLTAGE";
        case LogEvent::OVERTEMP:           return "OVERTEMP";
        case LogEvent::DISPLAY_INIT_OK:    return "DISPLAY_INIT_OK";
        case LogEvent::DISPLAY_INIT_FAIL:  return "DISPLAY_INIT_FAIL";
        case LogEvent::EINK_REFRESH:       return "EINK_REFRESH";
        case LogEvent::EINK_FAIL:          return "EINK_FAIL";
        case LogEvent::GENERIC_INFO:       return "GENERIC_INFO";
        case LogEvent::GENERIC_WARN:       return "GENERIC_WARN";
        case LogEvent::GENERIC_ERROR:      return "GENERIC_ERROR";
        case LogEvent::WATCHDOG_RESET:     return "WATCHDOG_RESET";
        case LogEvent::ASSERT_FAILED:      return "ASSERT_FAILED";
        case LogEvent::UNKNOWN:            return "UNKNOWN";
        default:                           return "?";
    }
}
