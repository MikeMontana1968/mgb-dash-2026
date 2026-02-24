#pragma once
/**
 * MGB Dash 2026 — CAN Log Library
 *
 * Emits structured log events over CAN (0x731 LOG + 0x732 LOG_TEXT).
 * Falls back to Serial.printf when CAN bus is unavailable.
 *
 * Usage:
 *   CanLog canLog;
 *   canLog.init(&canBus, LogRole::FUEL);
 *   canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_START);
 *   canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
 *   canLog.log(LogLevel::LOG_ERROR, LogEvent::TX_FAIL, errCode, "CAN timeout");
 */

#include <Arduino.h>
#include "can_ids.h"
#include "log_events.h"

class CanBus;  // forward declaration

class CanLog {
public:
    /**
     * Initialize the CAN logger.
     * @param canBus   Pointer to initialized CanBus instance (may be nullptr for Serial-only)
     * @param role     This module's LogRole
     */
    void init(CanBus* canBus, LogRole role);

    /** Log an event with no context. */
    void log(LogLevel level, LogEvent event);

    /** Log an event with a uint32 context value. */
    void log(LogLevel level, LogEvent event, uint32_t context);

    /** Log an event with a uint32 context value and text message. */
    void log(LogLevel level, LogEvent event, uint32_t context, const char* text);

    /** Set minimum log level (messages below this are discarded). Default: LOG_DEBUG. */
    void setMinLevel(LogLevel level) { minLevel_ = level; }

    /** Get current minimum log level. */
    LogLevel getMinLevel() const { return minLevel_; }

private:
    CanBus* canBus_ = nullptr;
    LogRole role_ = LogRole::FUEL;
    LogLevel minLevel_ = LogLevel::LOG_DEBUG;

    /** Check if CAN bus is available for transmission. */
    bool canAvailable_();

    /** Build and send the 8-byte LOG frame (0x731). */
    void sendLogFrame_(LogLevel level, LogEvent event, uint32_t context, uint8_t textFrames);

    /** Send text continuation frames (0x732). */
    void sendTextFrames_(const char* text, uint8_t frameCount);

    /** Fallback: print log to Serial when CAN is unavailable. */
    void serialFallback_(LogLevel level, LogEvent event, uint32_t context, const char* text);
};
