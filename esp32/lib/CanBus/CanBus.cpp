/**
 * MGB Dash 2026 — CAN Bus Library Implementation
 */

#include "CanBus.h"
#include "esp_log.h"

static const char* TAG = "CAN";

bool CanBus::init(int txPin, int rxPin, uint32_t speed) {
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(
        (gpio_num_t)txPin, (gpio_num_t)rxPin, TWAI_MODE_NORMAL);
    g_config.rx_queue_len = 32;
    g_config.tx_queue_len = 8;

    twai_timing_config_t t_config;
    if (speed == 500000) {
        t_config = TWAI_TIMING_CONFIG_500KBITS();
    } else if (speed == 250000) {
        t_config = TWAI_TIMING_CONFIG_250KBITS();
    } else {
        t_config = TWAI_TIMING_CONFIG_500KBITS();  // default
    }

    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

    esp_err_t err = twai_driver_install(&g_config, &t_config, &f_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Driver install failed: 0x%X", err);
        return false;
    }

    err = twai_start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Start failed: 0x%X", err);
        return false;
    }

    installed_ = true;
    busOff_ = false;
    ESP_LOGI(TAG, "Initialized at %lu bps (TX=%d, RX=%d)", speed, txPin, rxPin);
    return true;
}

bool CanBus::transmit(uint32_t id, const uint8_t* data, uint8_t len) {
    if (!installed_ || busOff_) return false;

    twai_message_t msg = {};
    msg.identifier = id;
    msg.data_length_code = len;
    msg.flags = 0;  // 11-bit standard frame
    memcpy(msg.data, data, len);

    esp_err_t err = twai_transmit(&msg, pdMS_TO_TICKS(10));
    if (err != ESP_OK) {
        txErrorCount_++;
        return false;
    }
    return true;
}

bool CanBus::safeTransmit(uint32_t id, const uint8_t* data, uint8_t len) {
    if (id < CAN_CUSTOM_ID_MIN || id > CAN_CUSTOM_ID_MAX) {
        ESP_LOGW(TAG, "BLOCKED transmit of non-custom ID 0x%03X", id);
        return false;
    }
    return transmit(id, data, len);
}

bool CanBus::receive(uint32_t& id, uint8_t* data, uint8_t& len) {
    if (!installed_ || busOff_) return false;

    twai_message_t msg;
    esp_err_t err = twai_receive(&msg, 0);  // non-blocking
    if (err != ESP_OK) return false;

    id = msg.identifier;
    len = msg.data_length_code;
    memcpy(data, msg.data, len);
    return true;
}

void CanBus::checkErrors() {
    if (!installed_) return;

    twai_status_info_t status;
    if (twai_get_status_info(&status) != ESP_OK) return;

    if (status.state == TWAI_STATE_BUS_OFF) {
        if (!busOff_) {
            busOff_ = true;
            ESP_LOGE(TAG, "Bus-off detected (tx_err=%lu, rx_err=%lu). "
                     "Check CAN wiring and pin assignments.",
                     status.tx_error_counter, status.rx_error_counter);
        }
    } else if (status.state == TWAI_STATE_RUNNING && busOff_) {
        busOff_ = false;
        ESP_LOGI(TAG, "Recovered from bus-off.");
    }

    // Track deltas — hardware registers are running totals, not increments
    if (status.tx_error_counter > lastTxErrSnapshot_) {
        txErrorCount_ += (status.tx_error_counter - lastTxErrSnapshot_);
    }
    lastTxErrSnapshot_ = status.tx_error_counter;

    if (status.rx_error_counter > lastRxErrSnapshot_) {
        rxErrorCount_ += (status.rx_error_counter - lastRxErrSnapshot_);
    }
    lastRxErrSnapshot_ = status.rx_error_counter;
}

bool CanBus::getStatus(twai_status_info_t& status) const {
    if (!installed_) return false;
    return twai_get_status_info(&status) == ESP_OK;
}
