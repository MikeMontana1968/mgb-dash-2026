#pragma once
/**
 * MGB Dash 2026 — Heartbeat Library
 *
 * Broadcasts module heartbeat at 1 Hz on CAN_ID_HEARTBEAT (0x700).
 * Payload: [role(5)] [uptime(1)] [errors(1)] [reserved(1)]
 */

#include <Arduino.h>
#include "can_ids.h"

class CanBus;  // forward declaration

class Heartbeat {
public:
    /**
     * Initialize heartbeat broadcaster.
     * @param canBus  Pointer to initialized CanBus instance
     * @param roleName  5-char role name (e.g., "FUEL ", "BODY ")
     */
    void init(CanBus* canBus, const char* roleName);

    /** Call every loop iteration. Broadcasts at 1 Hz. */
    void update();

    /** Set error flags byte (for future use). */
    void setErrorFlags(uint8_t flags) { errorFlags_ = flags; }

    /** Get rolling uptime counter value. */
    uint8_t getUptimeCounter() const { return uptimeCounter_; }

private:
    CanBus* canBus_ = nullptr;
    char roleName_[6] = {};  // 5 chars + null
    uint8_t uptimeCounter_ = 0;
    uint8_t errorFlags_ = 0;
    unsigned long lastBroadcastMs_ = 0;
};
