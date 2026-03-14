#pragma once
/**
 * MGB Dash 2026 — BLE CAN Client
 *
 * NimBLE client that connects to the MGB-AMPS BLE server and receives
 * CAN frames forwarded as 12-byte notifications (4-byte ID LE + 8-byte data).
 */

#include <NimBLEDevice.h>
#include <freertos/queue.h>

// Must match BleBridge UUIDs
#define BLE_SERVICE_UUID        "d4e0e0d0-1a2b-11e9-ab14-d663bd873d93"
#define BLE_CHARACTERISTIC_UUID "d4e0e0d1-1a2b-11e9-ab14-d663bd873d93"

struct CanFrame {
    uint32_t id;
    uint8_t data[8];
    uint8_t len;
};

typedef void (*CanFrameCallback)(const CanFrame& frame);

class BleClient {
public:
    void init();
    void setOnFrame(CanFrameCallback cb) { callback_ = cb; }
    void update();  // call from main loop — drains queue and fires callbacks
    bool isConnected() const { return connected_; }

private:
    bool connected_ = false;
    bool scanning_  = false;
    CanFrameCallback callback_ = nullptr;
    QueueHandle_t frameQueue_ = nullptr;

    NimBLEClient* pClient_ = nullptr;
    NimBLEAddress targetAddr_;
    bool targetFound_ = false;

    unsigned long lastReconnectMs_ = 0;
    static constexpr unsigned long RECONNECT_INTERVAL_MS = 2000;

    void startScan();
    bool connectToServer();

    // BLE notification callback (runs in NimBLE task context)
    static void notifyCb(NimBLERemoteCharacteristic* pChar,
                         uint8_t* pData, size_t length, bool isNotify);

    // Static reference for callbacks
    static BleClient* instance_;

    class ClientCallbacks : public NimBLEClientCallbacks {
    public:
        void onConnect(NimBLEClient* pClient) override;
        void onDisconnect(NimBLEClient* pClient) override;
    };

    class ScanCallbacks : public NimBLEAdvertisedDeviceCallbacks {
    public:
        void onResult(NimBLEAdvertisedDevice* advertisedDevice) override;
    };
};
