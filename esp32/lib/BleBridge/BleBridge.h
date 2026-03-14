#pragma once
/**
 * MGB Dash 2026 — BLE CAN Bridge
 *
 * NimBLE server that forwards selected CAN frames as BLE notifications.
 * Each notification is 12 bytes: 4-byte CAN ID (LE) + 8-byte data.
 */

#include <NimBLEDevice.h>

// Custom 128-bit UUIDs for MGB CAN bridge service
#define BLE_SERVICE_UUID        "d4e0e0d0-1a2b-11e9-ab14-d663bd873d93"
#define BLE_CHARACTERISTIC_UUID "d4e0e0d1-1a2b-11e9-ab14-d663bd873d93"

class BleBridge {
public:
    void init(const char* deviceName);
    void notifyCanFrame(uint32_t id, const uint8_t* data, uint8_t len);
    bool hasClient() const { return clientConnected_; }

private:
    NimBLEServer* pServer_ = nullptr;
    NimBLECharacteristic* pCharacteristic_ = nullptr;
    bool clientConnected_ = false;

    class ServerCallbacks : public NimBLEServerCallbacks {
    public:
        ServerCallbacks(BleBridge* bridge) : bridge_(bridge) {}
        void onConnect(NimBLEServer* pServer) override;
        void onDisconnect(NimBLEServer* pServer) override;
    private:
        BleBridge* bridge_;
    };
};
