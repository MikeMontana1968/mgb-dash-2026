#pragma once
/**
 * MGB Dash 2026 — QSPI Display Driver
 *
 * Driver for Waveshare ESP32-S3-LCD-1.85 (360x360, ST77916 via QSPI).
 * Initializes the LCD and registers as an LVGL display driver.
 */

#include <Arduino.h>
#include "lvgl.h"
#include <driver/spi_master.h>

class QspiDisplay {
public:
    static constexpr int WIDTH  = 360;
    static constexpr int HEIGHT = 360;

    bool init();
    void setBacklight(uint8_t duty);  // 0-100

    lv_display_t* getLvDisplay() { return lvDisplay_; }

private:
    lv_display_t* lvDisplay_ = nullptr;
    spi_device_handle_t spiDev_ = nullptr;

    // LVGL display buffers (PSRAM-backed)
    static constexpr int BUF_LINES = 40;
    uint8_t* buf1_ = nullptr;
    uint8_t* buf2_ = nullptr;

    void initBacklight();
    void initSPI();
    void initLCD();
    void initLvgl();

    // ST77916 QSPI write helpers
    void lcdWriteCmd(uint8_t cmd);
    void lcdWriteCmdData(uint8_t cmd, const uint8_t* data, int len);
    void lcdWritePixels(const uint8_t* data, uint32_t len);
    void lcdSetWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);

    static void lvFlushCb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map);
};
