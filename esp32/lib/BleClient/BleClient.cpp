#include "BleClient.h"
#include "esp_log.h"

static const char* TAG = "BLE_C";

BleClient* BleClient::instance_ = nullptr;

// ── Scan callbacks ──────────────────────────────────────────────────────

void BleClient::ScanCallbacks::onResult(NimBLEAdvertisedDevice* device) {
    if (device->isAdvertisingService(NimBLEUUID(BLE_SERVICE_UUID))) {
        ESP_LOGI(TAG, "Found MGB-AMPS server: %s", device->getAddress().toString().c_str());
        NimBLEDevice::getScan()->stop();
        instance_->targetAddr_ = device->getAddress();
        instance_->targetFound_ = true;
        instance_->scanning_ = false;
    }
}

// ── Client callbacks ────────────────────────────────────────────────────

void BleClient::ClientCallbacks::onConnect(NimBLEClient* pClient) {
    ESP_LOGI(TAG, "Connected to BLE server");
    instance_->connected_ = true;
}

void BleClient::ClientCallbacks::onDisconnect(NimBLEClient* pClient) {
    ESP_LOGW(TAG, "Disconnected from BLE server");
    instance_->connected_ = false;
    instance_->targetFound_ = false;
}

// ── Notification callback (NimBLE task context) ─────────────────────────

void BleClient::notifyCb(NimBLERemoteCharacteristic* pChar,
                         uint8_t* pData, size_t length, bool isNotify) {
    if (length < 12 || !instance_ || !instance_->frameQueue_) return;

    CanFrame frame;
    frame.id = (uint32_t)pData[0]
             | ((uint32_t)pData[1] << 8)
             | ((uint32_t)pData[2] << 16)
             | ((uint32_t)pData[3] << 24);
    frame.len = 8;
    memcpy(frame.data, pData + 4, 8);

    // Non-blocking enqueue — drop frame if queue is full
    xQueueSend(instance_->frameQueue_, &frame, 0);
}

// ── Init ────────────────────────────────────────────────────────────────

void BleClient::init() {
    instance_ = this;

    frameQueue_ = xQueueCreate(32, sizeof(CanFrame));

    NimBLEDevice::init("MGB-GPS-DISP");
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);

    pClient_ = NimBLEDevice::createClient();
    pClient_->setClientCallbacks(new ClientCallbacks());

    ESP_LOGI(TAG, "BLE client initialized, starting scan...");
    startScan();
}

// ── Scanning ────────────────────────────────────────────────────────────

void BleClient::startScan() {
    if (scanning_) return;
    scanning_ = true;

    NimBLEScan* pScan = NimBLEDevice::getScan();
    pScan->setAdvertisedDeviceCallbacks(new ScanCallbacks());
    pScan->setActiveScan(true);
    pScan->setInterval(100);
    pScan->setWindow(99);
    pScan->start(5, false);  // scan for 5 seconds, non-blocking

    ESP_LOGI(TAG, "BLE scan started");
}

// ── Connect to discovered server ────────────────────────────────────────

bool BleClient::connectToServer() {
    ESP_LOGI(TAG, "Connecting to %s...", targetAddr_.toString().c_str());

    if (!pClient_->connect(targetAddr_)) {
        ESP_LOGW(TAG, "Connection failed");
        targetFound_ = false;
        return false;
    }

    NimBLERemoteService* pService = pClient_->getService(BLE_SERVICE_UUID);
    if (!pService) {
        ESP_LOGW(TAG, "Service not found");
        pClient_->disconnect();
        targetFound_ = false;
        return false;
    }

    NimBLERemoteCharacteristic* pChar = pService->getCharacteristic(BLE_CHARACTERISTIC_UUID);
    if (!pChar) {
        ESP_LOGW(TAG, "Characteristic not found");
        pClient_->disconnect();
        targetFound_ = false;
        return false;
    }

    if (!pChar->subscribe(true, notifyCb)) {
        ESP_LOGW(TAG, "Subscribe failed");
        pClient_->disconnect();
        targetFound_ = false;
        return false;
    }

    ESP_LOGI(TAG, "Subscribed to CAN frame notifications");
    return true;
}

// ── Main-loop update ────────────────────────────────────────────────────

void BleClient::update() {
    unsigned long now = millis();

    // If disconnected and target found, try connecting
    if (!connected_ && targetFound_) {
        if (now - lastReconnectMs_ >= RECONNECT_INTERVAL_MS) {
            lastReconnectMs_ = now;
            connectToServer();
        }
    }

    // If disconnected and no target, scan periodically
    if (!connected_ && !targetFound_ && !scanning_) {
        if (now - lastReconnectMs_ >= RECONNECT_INTERVAL_MS) {
            lastReconnectMs_ = now;
            startScan();
        }
    }

    // Check if scan finished without finding target
    if (scanning_ && !NimBLEDevice::getScan()->isScanning()) {
        scanning_ = false;
        if (!targetFound_) {
            ESP_LOGD(TAG, "Scan complete, server not found");
        }
    }

    // Drain frame queue
    if (callback_ && frameQueue_) {
        CanFrame frame;
        while (xQueueReceive(frameQueue_, &frame, 0) == pdTRUE) {
            callback_(frame);
        }
    }
}
