/**
 * MGB Dash 2026 — CAN Log Library Implementation
 */

#include "CanLog.h"
#include "CanBus.h"
#include <cstring>
#include "esp_log.h"

static const char* TAG = "CANLOG";

void CanLog::init(CanBus* canBus, LogRole role) {
    canBus_ = canBus;
    role_ = role;
    minLevel_ = LogLevel::LOG_DEBUG;
}

void CanLog::log(LogLevel level, LogEvent event) {
    log(level, event, 0, nullptr);
}

void CanLog::log(LogLevel level, LogEvent event, uint32_t context) {
    log(level, event, context, nullptr);
}

void CanLog::log(LogLevel level, LogEvent event, uint32_t context, const char* text) {
    // Filter by minimum level
    if (static_cast<uint8_t>(level) < static_cast<uint8_t>(minLevel_)) return;

    // Calculate text frame count
    uint8_t textFrames = 0;
    if (text && text[0] != '\0') {
        size_t len = strlen(text);
        textFrames = (len + LOG_TEXT_CHARS_PER_FRAME - 1) / LOG_TEXT_CHARS_PER_FRAME;
        if (textFrames > LOG_TEXT_MAX_FRAMES) textFrames = LOG_TEXT_MAX_FRAMES;
    }

    if (canAvailable_()) {
        sendLogFrame_(level, event, context, textFrames);
        if (textFrames > 0) {
            sendTextFrames_(text, textFrames);
        }
    } else {
        serialFallback_(level, event, context, text);
    }
}

bool CanLog::canAvailable_() {
    if (!canBus_) return false;
    if (canBus_->isBusOff()) return false;
    return true;
}

void CanLog::sendLogFrame_(LogLevel level, LogEvent event, uint32_t context, uint8_t textFrames) {
    uint8_t payload[LOG_DLC] = {};
    payload[0] = packRoleLevel(role_, level);
    payload[1] = static_cast<uint8_t>(event);
    // Context value — big-endian
    payload[2] = (context >> 24) & 0xFF;
    payload[3] = (context >> 16) & 0xFF;
    payload[4] = (context >> 8)  & 0xFF;
    payload[5] = context & 0xFF;
    payload[6] = 0x00;  // reserved
    payload[7] = textFrames;

    canBus_->safeTransmit(CAN_ID_LOG, payload, LOG_DLC);
}

void CanLog::sendTextFrames_(const char* text, uint8_t frameCount) {
    size_t len = strlen(text);
    for (uint8_t i = 0; i < frameCount; i++) {
        uint8_t payload[LOG_TEXT_DLC] = {};
        payload[0] = i;  // fragment index

        size_t offset = i * LOG_TEXT_CHARS_PER_FRAME;
        size_t remaining = (offset < len) ? len - offset : 0;
        size_t copyLen = (remaining < LOG_TEXT_CHARS_PER_FRAME) ? remaining : LOG_TEXT_CHARS_PER_FRAME;
        memcpy(&payload[1], text + offset, copyLen);
        // Remaining bytes are already 0 (null-padded)

        canBus_->safeTransmit(CAN_ID_LOG_TEXT, payload, LOG_TEXT_DLC);
    }
}

void CanLog::serialFallback_(LogLevel level, LogEvent event, uint32_t context, const char* text) {
    if (text && text[0] != '\0') {
        ESP_LOGI(TAG, "%s %s %s ctx=%lu %s",
            roleName(role_), levelName(level), eventName(event),
            (unsigned long)context, text);
    } else {
        ESP_LOGI(TAG, "%s %s %s ctx=%lu",
            roleName(role_), levelName(level), eventName(event),
            (unsigned long)context);
    }
}
