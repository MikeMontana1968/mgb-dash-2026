#include "QspiDisplay.h"
#include "esp_log.h"
#include <driver/ledc.h>
#include <esp_heap_caps.h>

static const char* TAG = "QSPI";

// ── ST77916 QSPI Protocol ──────────────────────────────────────────────
// Command write (single-wire): cmd byte 0x02 + 24-bit addr (reg<<8) + params
// Pixel write (quad-wire):     cmd byte 0x32 + 24-bit addr (0x2C<<8) + pixels

void QspiDisplay::lcdWriteCmd(uint8_t cmd) {
    spi_transaction_t t = {};
    t.flags = SPI_TRANS_MULTILINE_CMD | SPI_TRANS_MULTILINE_ADDR;
    t.cmd = 0x02;
    t.addr = ((uint32_t)cmd) << 8;
    t.length = 0;
    spi_device_polling_transmit(spiDev_, &t);
}

void QspiDisplay::lcdWriteCmdData(uint8_t cmd, const uint8_t* data, int len) {
    spi_transaction_t t = {};
    t.cmd = 0x02;
    t.addr = ((uint32_t)cmd) << 8;
    t.tx_buffer = data;
    t.length = len * 8;
    spi_device_polling_transmit(spiDev_, &t);
}

void QspiDisplay::lcdWritePixels(const uint8_t* data, uint32_t len) {
    spi_transaction_t t = {};
    t.flags = SPI_TRANS_MODE_QIO;
    t.cmd = 0x32;
    t.addr = 0x002C00;
    t.tx_buffer = data;
    t.length = len * 8;
    spi_device_polling_transmit(spiDev_, &t);
}

void QspiDisplay::lcdSetWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
    uint8_t colData[] = { (uint8_t)(x0 >> 8), (uint8_t)(x0 & 0xFF),
                          (uint8_t)(x1 >> 8), (uint8_t)(x1 & 0xFF) };
    uint8_t rowData[] = { (uint8_t)(y0 >> 8), (uint8_t)(y0 & 0xFF),
                          (uint8_t)(y1 >> 8), (uint8_t)(y1 & 0xFF) };
    lcdWriteCmdData(0x2A, colData, 4);  // Column address set
    lcdWriteCmdData(0x2B, rowData, 4);  // Row address set
}

// ── Backlight (LEDC PWM on GPIO5) ───────────────────────────────────────

void QspiDisplay::initBacklight() {
    ledc_timer_config_t timer_conf = {};
    timer_conf.speed_mode = LEDC_LOW_SPEED_MODE;
    timer_conf.timer_num  = LEDC_TIMER_0;
    timer_conf.duty_resolution = LEDC_TIMER_8_BIT;
    timer_conf.freq_hz    = 5000;
    timer_conf.clk_cfg    = LEDC_AUTO_CLK;
    ledc_timer_config(&timer_conf);

    ledc_channel_config_t ch_conf = {};
    ch_conf.speed_mode = LEDC_LOW_SPEED_MODE;
    ch_conf.channel    = LEDC_CHANNEL_0;
    ch_conf.timer_sel  = LEDC_TIMER_0;
    ch_conf.gpio_num   = PIN_LCD_BL;
    ch_conf.duty       = 255;  // full brightness initially
    ch_conf.hpoint     = 0;
    ledc_channel_config(&ch_conf);
}

void QspiDisplay::setBacklight(uint8_t duty) {
    // duty: 0-100 percent
    uint32_t d = (duty > 100) ? 255 : (duty * 255 / 100);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, d);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

// ── SPI bus init ────────────────────────────────────────────────────────

void QspiDisplay::initSPI() {
    spi_bus_config_t bus_cfg = {};
    bus_cfg.mosi_io_num    = PIN_LCD_SDA0;
    bus_cfg.miso_io_num    = PIN_LCD_SDA1;
    bus_cfg.sclk_io_num    = PIN_LCD_SCK;
    bus_cfg.quadwp_io_num  = PIN_LCD_SDA2;
    bus_cfg.quadhd_io_num  = PIN_LCD_SDA3;
    bus_cfg.data4_io_num   = -1;
    bus_cfg.data5_io_num   = -1;
    bus_cfg.data6_io_num   = -1;
    bus_cfg.data7_io_num   = -1;
    bus_cfg.max_transfer_sz = WIDTH * BUF_LINES * 2 + 64;
    bus_cfg.flags          = SPICOMMON_BUSFLAG_MASTER | SPICOMMON_BUSFLAG_QUAD;

    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO));

    spi_device_interface_config_t dev_cfg = {};
    dev_cfg.command_bits   = 8;
    dev_cfg.address_bits   = 24;
    dev_cfg.mode           = 0;
    dev_cfg.clock_speed_hz = 40 * 1000 * 1000;  // 40 MHz
    dev_cfg.spics_io_num   = PIN_LCD_CS;
    dev_cfg.queue_size     = 10;
    dev_cfg.flags          = SPI_DEVICE_HALFDUPLEX;

    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &dev_cfg, &spiDev_));
    ESP_LOGI(TAG, "SPI bus initialized (40 MHz QSPI)");
}

// ── ST77916 LCD initialization ──────────────────────────────────────────

void QspiDisplay::initLCD() {
    // Hardware reset via TE pin (active low pulse) — optional
    // The Waveshare board may use a separate RST GPIO; skip if not wired.

    // Sleep Out
    lcdWriteCmd(0x11);
    delay(120);

    // Normal Display Mode On
    lcdWriteCmd(0x13);

    // Display Inversion On (typical for IPS panels)
    lcdWriteCmd(0x21);

    // Pixel Format: 16-bit RGB565
    uint8_t pixfmt = 0x55;
    lcdWriteCmdData(0x3A, &pixfmt, 1);

    // Memory Access Control: row/col order for correct orientation
    // Adjust this byte based on desired rotation:
    //   0x00 = normal, 0x60 = 90° CW, 0xC0 = 180°, 0xA0 = 270°
    // Bit 3 = BGR subpixel order (required for ST77916 IPS panel)
    uint8_t madctl = 0x08;
    lcdWriteCmdData(0x36, &madctl, 1);

    // Tearing Effect Line ON (rising edge)
    uint8_t teon = 0x00;
    lcdWriteCmdData(0x35, &teon, 1);

    // Set column address (0..359)
    lcdSetWindow(0, 0, WIDTH - 1, HEIGHT - 1);

    // Display ON
    lcdWriteCmd(0x29);
    delay(20);

    ESP_LOGI(TAG, "ST77916 LCD initialized (%dx%d)", WIDTH, HEIGHT);
}

// ── LVGL display integration ────────────────────────────────────────────

void QspiDisplay::lvFlushCb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map) {
    QspiDisplay* self = (QspiDisplay*)lv_display_get_user_data(disp);

    uint16_t x0 = area->x1;
    uint16_t y0 = area->y1;
    uint16_t x1 = area->x2;
    uint16_t y1 = area->y2;

    self->lcdSetWindow(x0, y0, x1, y1);

    uint32_t len = (x1 - x0 + 1) * (y1 - y0 + 1) * 2;  // RGB565 = 2 bytes/pixel
    self->lcdWritePixels(px_map, len);

    lv_display_flush_ready(disp);
}

void QspiDisplay::initLvgl() {
    uint32_t bufSize = WIDTH * BUF_LINES * sizeof(lv_color16_t);
    buf1_ = (uint8_t*)heap_caps_malloc(bufSize, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    buf2_ = (uint8_t*)heap_caps_malloc(bufSize, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);

    if (!buf1_ || !buf2_) {
        ESP_LOGE(TAG, "Failed to allocate LVGL display buffers");
        return;
    }

    lvDisplay_ = lv_display_create(WIDTH, HEIGHT);
    lv_display_set_flush_cb(lvDisplay_, lvFlushCb);
    lv_display_set_user_data(lvDisplay_, this);
    lv_display_set_buffers(lvDisplay_, buf1_, buf2_, bufSize,
                           LV_DISPLAY_RENDER_MODE_PARTIAL);

    ESP_LOGI(TAG, "LVGL display registered (%dx%d, %d-line buffers)", WIDTH, HEIGHT, BUF_LINES);
}

// ── Public init ─────────────────────────────────────────────────────────

bool QspiDisplay::init() {
    ESP_LOGI(TAG, "Initializing Waveshare ESP32-S3-LCD-1.85...");
    initBacklight();
    initSPI();
    initLCD();
    initLvgl();
    return (lvDisplay_ != nullptr);
}
