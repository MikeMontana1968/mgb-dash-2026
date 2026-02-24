/**
 * MGB Dash 2026 — Heartbeat Library Implementation
 */

#include "Heartbeat.h"
#include "CanBus.h"

void Heartbeat::init(CanBus* canBus, const char* roleName) {
    canBus_ = canBus;
    memset(roleName_, ' ', 5);
    strncpy(roleName_, roleName, 5);
    uptimeCounter_ = 0;
    errorFlags_ = 0;
    lastBroadcastMs_ = 0;
}

void Heartbeat::update() {
    if (!canBus_) return;

    unsigned long now = millis();
    if (now - lastBroadcastMs_ < HEARTBEAT_INTERVAL_MS) return;
    lastBroadcastMs_ = now;

    uint8_t payload[HEARTBEAT_LEN] = {};
    memcpy(&payload[HB_ROLE_OFFSET], roleName_, HB_ROLE_LEN);
    payload[HB_UPTIME_OFFSET] = uptimeCounter_;
    payload[HB_ERROR_OFFSET] = errorFlags_;
    payload[HB_RESERVED_OFFSET] = 0x00;

    canBus_->safeTransmit(CAN_ID_HEARTBEAT, payload, HEARTBEAT_LEN);
    uptimeCounter_++;  // wraps at 255
}
