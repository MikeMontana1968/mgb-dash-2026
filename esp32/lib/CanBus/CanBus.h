#pragma once
/**
 * MGB Dash 2026 — CAN Bus Library
 *
 * ESP32 TWAI driver wrapper with transmit ID range guards,
 * error handling, and bus-off recovery.
 */

#include <Arduino.h>
#include <driver/twai.h>
#include "can_ids.h"

class CanBus {
public:
    /**
     * Initialize TWAI driver.
     * @param txPin  GPIO for CAN TX (to TJA1050)
     * @param rxPin  GPIO for CAN RX (from TJA1050)
     * @param speed  Bus speed in bps (500000 for 500 kbps)
     */
    bool init(int txPin, int rxPin, uint32_t speed);

    /**
     * Transmit a CAN frame.
     * @return true if transmitted successfully
     */
    bool transmit(uint32_t id, const uint8_t* data, uint8_t len);

    /**
     * Transmit with ID range guard — only allows custom IDs (0x700–0x73F).
     * Prevents accidental transmission of Leaf CAN IDs.
     * @return true if transmitted, false if ID out of range or error
     */
    bool safeTransmit(uint32_t id, const uint8_t* data, uint8_t len);

    /**
     * Receive a CAN frame (non-blocking).
     * @return true if a frame was received
     */
    bool receive(uint32_t& id, uint8_t* data, uint8_t& len);

    /** Check for and recover from bus-off state. Call periodically. */
    void checkErrors();

    /** Get cumulative error counts. */
    uint32_t getTxErrorCount() const { return txErrorCount_; }
    uint32_t getRxErrorCount() const { return rxErrorCount_; }
    bool isBusOff() const { return busOff_; }

private:
    bool installed_ = false;
    bool busOff_ = false;
    uint32_t txErrorCount_ = 0;
    uint32_t rxErrorCount_ = 0;
    unsigned long lastRecoveryAttemptMs_ = 0;
    static constexpr unsigned long RECOVERY_BACKOFF_MS = 500;
};
