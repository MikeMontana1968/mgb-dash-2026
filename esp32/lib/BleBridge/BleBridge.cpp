#include "BleBridge.h"
#include "esp_log.h"

static const char* TAG = "BLE";

void BleBridge::ServerCallbacks::onConnect(NimBLEServer* pServer) {
    bridge_->clientConnected_ = true;
    ESP_LOGI(TAG, "BLE client connected");
}

void BleBridge::ServerCallbacks::onDisconnect(NimBLEServer* pServer) {
    bridge_->clientConnected_ = false;
    ESP_LOGI(TAG, "BLE client disconnected — restarting advertising");
    NimBLEDevice::startAdvertising();
}

void BleBridge::init(const char* deviceName) {
    ESP_LOGI(TAG, "Initializing BLE server as '%s'", deviceName);

    NimBLEDevice::init(deviceName);
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);

    pServer_ = NimBLEDevice::createServer();
    pServer_->setCallbacks(new ServerCallbacks(this));

    NimBLEService* pService = pServer_->createService(BLE_SERVICE_UUID);
    pCharacteristic_ = pService->createCharacteristic(
        BLE_CHARACTERISTIC_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    pService->start();

    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(BLE_SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->start();

    ESP_LOGI(TAG, "BLE server started, advertising");
}

void BleBridge::notifyCanFrame(uint32_t id, const uint8_t* data, uint8_t len) {
    if (!clientConnected_ || pCharacteristic_ == nullptr) return;

    uint8_t buf[12] = {0};
    // 4-byte CAN ID, little-endian
    buf[0] = (uint8_t)(id & 0xFF);
    buf[1] = (uint8_t)((id >> 8) & 0xFF);
    buf[2] = (uint8_t)((id >> 16) & 0xFF);
    buf[3] = (uint8_t)((id >> 24) & 0xFF);
    // 8-byte data (pad with zeros if len < 8)
    for (uint8_t i = 0; i < len && i < 8; i++) {
        buf[4 + i] = data[i];
    }

    pCharacteristic_->setValue(buf, 12);
    pCharacteristic_->notify();
}
