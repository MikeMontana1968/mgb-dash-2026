#pragma once
/**
 * MGB Dash 2026 — Clock Dial Renderer
 *
 * LVGL canvas-based 24-hour clock dial with sun/moon arcs, time, date,
 * speed, and moon phase. Port of python/gps-display/presenter.py.
 *
 * Scale: 360x360 (1.5x of original 240x240).
 */

#include "lvgl.h"

class ClockDial {
public:
    void init(lv_obj_t* parent);

    /** Update dial with fresh GPS data. All times are LOCAL. */
    void setData(int hour, int minute, int second,
                 int day, int month, int year, int dow,
                 double speedMph, double lat, double lng);

    /** Show "Waiting for GPS" + elapsed seconds counter. */
    void showWaiting(int elapsedSecs);

    /** Show fallback: time string + "signal lost". */
    void showSignalLost(const char* timeStr);

    /** Show "Connecting..." screen. */
    void showConnecting();

    /** Adjust backlight based on ambient category (0-3). */
    void setAmbient(uint8_t category);

private:
    static constexpr int W = 360;
    static constexpr int H = 360;
    static constexpr int CX = 180;
    static constexpr int CY = 180;
    static constexpr double ROTATION_OFFSET = 90.0;  // degrees
    static constexpr double DEG_PER_HOUR = 15.0;     // 360/24

    lv_obj_t* canvas_ = nullptr;
    lv_color_t* canvasBuf_ = nullptr;

    // Cached data for blink animation
    int curHour_ = 0, curMin_ = 0;
    bool blinkState_ = false;
    unsigned long lastBlinkMs_ = 0;

    // Drawing helpers
    void clearCanvas();
    void drawSunArc(double lat, double lng, int year, int month, int day);
    void drawMoonArc(double lat, double lng, int year, int month, int day);
    void drawHourTicks();
    void drawCurrentTimeTick(int hour, int minute);
    void drawMoonPhase(int year, int month, int day, int hour, int minute);
    void drawTimeText(int hour, int minute);
    void drawDateText(int day, int month, int year, int dow);
    void drawSpeedText(double speedMph);
    void drawCenteredText(const char* text, const lv_font_t* font,
                          lv_color_t color, int yCenter);

    // Coordinate from angle (24h clock mapping)
    void sinCos(int radius, double angleDeg, int& outX, int& outY);
};
