#include "ClockDial.h"
#include "Ephemeris.h"
#include <Arduino.h>
#include <cmath>
#include <cstdio>
#include <esp_heap_caps.h>

// Use M_PI or Arduino's PI macro — avoid redefining
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// ── Day-of-week abbreviations ───────────────────────────────────────────
static const char* DOW_NAMES[] = {
    "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"
};
static const char* MONTH_NAMES[] = {
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
};

// ── Init ────────────────────────────────────────────────────────────────

void ClockDial::init(lv_obj_t* parent) {
    // Allocate canvas buffer in PSRAM (360*360*2 = 259,200 bytes)
    canvasBuf_ = (lv_color_t*)heap_caps_malloc(
        W * H * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

    if (!canvasBuf_) {
        // Fallback to internal RAM (unlikely to fit, but try)
        canvasBuf_ = (lv_color_t*)malloc(W * H * sizeof(lv_color_t));
    }

    canvas_ = lv_canvas_create(parent);
    lv_canvas_set_buffer(canvas_, canvasBuf_, W, H, LV_COLOR_FORMAT_RGB565);
    lv_obj_center(canvas_);

    clearCanvas();
}

// ── Canvas helpers ──────────────────────────────────────────────────────

void ClockDial::clearCanvas() {
    lv_canvas_fill_bg(canvas_, lv_color_black(), LV_OPA_COVER);
}

void ClockDial::sinCos(int radius, double angleDeg, int& outX, int& outY) {
    double angleRad = angleDeg * M_PI / 180.0;
    outX = CX + (int)(radius * sin(angleRad));
    outY = CY + (int)(radius * cos(angleRad));
}

void ClockDial::drawCenteredText(const char* text, const lv_font_t* font,
                                  lv_color_t color, int yCenter) {
    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_label_dsc_t dsc;
    lv_draw_label_dsc_init(&dsc);
    dsc.color = color;
    dsc.font  = font;
    dsc.text  = text;
    dsc.align = LV_TEXT_ALIGN_CENTER;

    // Estimate text height from font line height
    int fontH = lv_font_get_line_height(font);
    lv_area_t coords;
    coords.x1 = 0;
    coords.y1 = yCenter - fontH / 2;
    coords.x2 = W - 1;
    coords.y2 = yCenter + fontH / 2;

    lv_draw_label(&layer, &dsc, &coords);

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Sun arc ─────────────────────────────────────────────────────────────

void ClockDial::drawSunArc(double lat, double lng, int year, int month, int day) {
    Ephemeris::SunTimes sun = Ephemeris::getSunTimes(year, month, day, lat, lng);

    int startAngle = (int)(ROTATION_OFFSET + DEG_PER_HOUR * sun.rise);
    int endAngle   = (int)(ROTATION_OFFSET + DEG_PER_HOUR * sun.set);

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_arc_dsc_t dsc;
    lv_draw_arc_dsc_init(&dsc);
    dsc.center.x   = CX;
    dsc.center.y   = CY;
    dsc.radius     = 175;
    dsc.start_angle = startAngle;
    dsc.end_angle   = endAngle;
    dsc.width       = 15;
    dsc.color       = lv_color_make(255, 255, 0);  // yellow
    dsc.opa         = LV_OPA_COVER;

    lv_draw_arc(&layer, &dsc);
    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Moon arc ────────────────────────────────────────────────────────────

void ClockDial::drawMoonArc(double lat, double lng, int year, int month, int day) {
    Ephemeris::MoonTimes moon = Ephemeris::getMoonTimes(year, month, day, lat, lng);

    double rise = (moon.rise >= 0) ? moon.rise : 0.0;
    double set  = (moon.set  >= 0) ? moon.set  : 24.0;

    int startAngle = (int)(ROTATION_OFFSET + DEG_PER_HOUR * rise);
    int endAngle   = (int)(ROTATION_OFFSET + DEG_PER_HOUR * set);

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_arc_dsc_t dsc;
    lv_draw_arc_dsc_init(&dsc);
    dsc.center.x   = CX;
    dsc.center.y   = CY;
    dsc.radius     = 178;
    dsc.start_angle = startAngle;
    dsc.end_angle   = endAngle;
    dsc.width       = 30;
    dsc.color       = lv_color_make(80, 80, 80);  // gray
    dsc.opa         = LV_OPA_COVER;

    lv_draw_arc(&layer, &dsc);
    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Hour ticks ──────────────────────────────────────────────────────────

void ClockDial::drawHourTicks() {
    int hours[] = { 0, 6, 12, 18 };

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    for (int h : hours) {
        double angle = -(double)h * (360.0 / 24.0);
        int x1, y1, x2, y2;
        sinCos(W / 2, angle, x1, y1);
        sinCos(150, angle, x2, y2);

        lv_draw_line_dsc_t dsc;
        lv_draw_line_dsc_init(&dsc);
        dsc.p1.x = x1;
        dsc.p1.y = y1;
        dsc.p2.x = x2;
        dsc.p2.y = y2;
        dsc.color = lv_color_make(100, 100, 100);
        dsc.width = 5;
        dsc.opa   = LV_OPA_COVER;

        lv_draw_line(&layer, &dsc);
    }

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Current time tick (blinking) ────────────────────────────────────────

void ClockDial::drawCurrentTimeTick(int hour, int minute) {
    double h = hour + minute / 60.0;
    double angle = -h * (360.0 / 24.0);

    unsigned long now = millis();
    if (now - lastBlinkMs_ >= 500) {
        blinkState_ = !blinkState_;
        lastBlinkMs_ = now;
    }

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    int x1, y1, x2, y2;
    sinCos(W / 2, angle, x1, y1);
    sinCos(150, angle, x2, y2);

    // Thick background line
    lv_draw_line_dsc_t dsc;
    lv_draw_line_dsc_init(&dsc);
    dsc.p1.x = x1; dsc.p1.y = y1;
    dsc.p2.x = x2; dsc.p2.y = y2;
    dsc.color = blinkState_ ? lv_color_white() : lv_color_black();
    dsc.width = 15;
    dsc.opa   = LV_OPA_COVER;
    lv_draw_line(&layer, &dsc);

    // Thin inner line (opposite color)
    lv_draw_line_dsc_t dsc2;
    lv_draw_line_dsc_init(&dsc2);
    dsc2.p1.x = x1; dsc2.p1.y = y1;
    dsc2.p2.x = x2; dsc2.p2.y = y2;
    dsc2.color = blinkState_ ? lv_color_black() : lv_color_white();
    dsc2.width = 5;
    dsc2.opa   = LV_OPA_COVER;
    lv_draw_line(&layer, &dsc2);

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Moon phase icon ─────────────────────────────────────────────────────

void ClockDial::drawMoonPhase(int year, int month, int day, int hour, int minute) {
    Ephemeris::MoonIllumination illum =
        Ephemeris::getMoonIllumination(year, month, day, hour, minute, 0);

    // Map phase (0-1) to a simple text representation
    // When custom moon_phases.ttf is loaded via FreeType, replace with glyph
    const char* phaseStr;
    double p = illum.phase;
    if (p < 0.125)      phaseStr = "NEW";
    else if (p < 0.375) phaseStr = ")";    // waxing crescent/quarter
    else if (p < 0.625) phaseStr = "O";    // full
    else if (p < 0.875) phaseStr = "(";    // waning
    else                phaseStr = "NEW";

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_label_dsc_t dsc;
    lv_draw_label_dsc_init(&dsc);
    dsc.color = lv_color_white();
    dsc.font  = &lv_font_montserrat_28;
    dsc.text  = phaseStr;
    dsc.align = LV_TEXT_ALIGN_CENTER;

    int fontH = lv_font_get_line_height(dsc.font);
    lv_area_t coords = { 80, 290, 280, 290 + fontH };
    lv_draw_label(&layer, &dsc, &coords);

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Time text (large, centered) ─────────────────────────────────────────

void ClockDial::drawTimeText(int hour, int minute) {
    // Convert 24h to 12h format
    int h12 = hour % 12;
    if (h12 == 0) h12 = 12;

    char buf[8];
    snprintf(buf, sizeof(buf), "%d:%02d", h12, minute);

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_label_dsc_t dsc;
    lv_draw_label_dsc_init(&dsc);
    dsc.color = lv_color_white();
    dsc.font  = &lv_font_montserrat_48;  // largest built-in; swap for 80pt FreeType later
    dsc.text  = buf;
    dsc.align = LV_TEXT_ALIGN_CENTER;

    int fontH = lv_font_get_line_height(dsc.font);
    int yCenter = CY - 30;  // above center
    lv_area_t coords = { 0, yCenter - fontH / 2, W - 1, yCenter + fontH / 2 };
    lv_draw_label(&layer, &dsc, &coords);

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Date text ───────────────────────────────────────────────────────────

void ClockDial::drawDateText(int day, int month, int year, int dow) {
    char buf[20];
    const char* dowName = (dow >= 0 && dow <= 6) ? DOW_NAMES[dow] : "???";
    const char* monName = (month >= 1 && month <= 12) ? MONTH_NAMES[month] : "???";
    snprintf(buf, sizeof(buf), "%s %d %s", dowName, day, monName);

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_label_dsc_t dsc;
    lv_draw_label_dsc_init(&dsc);
    dsc.color = lv_color_make(200, 200, 200);
    dsc.font  = &lv_font_montserrat_36;
    dsc.text  = buf;
    dsc.align = LV_TEXT_ALIGN_CENTER;

    int fontH = lv_font_get_line_height(dsc.font);
    int yCenter = 248;  // below center, scaled from 165 * 1.5
    lv_area_t coords = { 0, yCenter - fontH / 2, W - 1, yCenter + fontH / 2 };
    lv_draw_label(&layer, &dsc, &coords);

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Speed text (top) ────────────────────────────────────────────────────

void ClockDial::drawSpeedText(double speedMph) {
    char buf[16];
    snprintf(buf, sizeof(buf), "%d mph", (int)round(speedMph));

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_label_dsc_t dsc;
    lv_draw_label_dsc_init(&dsc);
    dsc.color = lv_color_make(200, 200, 200);
    dsc.font  = &lv_font_montserrat_28;
    dsc.text  = buf;
    dsc.align = LV_TEXT_ALIGN_CENTER;

    int fontH = lv_font_get_line_height(dsc.font);
    int yCenter = 60;  // top area
    lv_area_t coords = { 0, yCenter - fontH / 2, W - 1, yCenter + fontH / 2 };
    lv_draw_label(&layer, &dsc, &coords);

    lv_canvas_finish_layer(canvas_, &layer);
}

// ── Public API ──────────────────────────────────────────────────────────

void ClockDial::setData(int hour, int minute, int second,
                         int day, int month, int year, int dow,
                         double speedMph, double lat, double lng) {
    curHour_ = hour;
    curMin_  = minute;

    clearCanvas();
    drawSpeedText(speedMph);
    drawMoonArc(lat, lng, year, month, day);
    drawSunArc(lat, lng, year, month, day);
    drawHourTicks();
    drawMoonPhase(year, month, day, hour, minute);
    drawCurrentTimeTick(hour, minute);
    drawDateText(day, month, year, dow);
    drawTimeText(hour, minute);
}

void ClockDial::showWaiting(int elapsedSecs) {
    clearCanvas();

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    // "Waiting for BLE" label
    lv_draw_label_dsc_t dsc1;
    lv_draw_label_dsc_init(&dsc1);
    dsc1.color = lv_color_make(255, 0, 0);
    dsc1.font  = &lv_font_montserrat_28;
    dsc1.text  = "Waiting for BLE";
    dsc1.align = LV_TEXT_ALIGN_CENTER;
    int fh1 = lv_font_get_line_height(dsc1.font);
    lv_area_t c1 = { 0, CY - 50 - fh1/2, W-1, CY - 50 + fh1/2 };
    lv_draw_label(&layer, &dsc1, &c1);

    // Elapsed seconds counter
    char buf[8];
    snprintf(buf, sizeof(buf), "%d", elapsedSecs);

    lv_draw_label_dsc_t dsc2;
    lv_draw_label_dsc_init(&dsc2);
    dsc2.color = lv_color_make(255, 0, 0);
    dsc2.font  = &lv_font_montserrat_48;
    dsc2.text  = buf;
    dsc2.align = LV_TEXT_ALIGN_CENTER;
    int fh2 = lv_font_get_line_height(dsc2.font);
    lv_area_t c2 = { 0, CY + 20 - fh2/2, W-1, CY + 20 + fh2/2 };
    lv_draw_label(&layer, &dsc2, &c2);

    lv_canvas_finish_layer(canvas_, &layer);
}

void ClockDial::showSignalLost(const char* timeStr) {
    clearCanvas();

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    // Time string
    lv_draw_label_dsc_t dsc1;
    lv_draw_label_dsc_init(&dsc1);
    dsc1.color = lv_color_white();
    dsc1.font  = &lv_font_montserrat_48;
    dsc1.text  = timeStr;
    dsc1.align = LV_TEXT_ALIGN_CENTER;
    int fh1 = lv_font_get_line_height(dsc1.font);
    lv_area_t c1 = { 0, CY - 30 - fh1/2, W-1, CY - 30 + fh1/2 };
    lv_draw_label(&layer, &dsc1, &c1);

    // "signal lost" label
    lv_draw_label_dsc_t dsc2;
    lv_draw_label_dsc_init(&dsc2);
    dsc2.color = lv_color_make(255, 0, 0);
    dsc2.font  = &lv_font_montserrat_28;
    dsc2.text  = "signal lost";
    dsc2.align = LV_TEXT_ALIGN_CENTER;
    int fh2 = lv_font_get_line_height(dsc2.font);
    lv_area_t c2 = { 0, CY + 40 - fh2/2, W-1, CY + 40 + fh2/2 };
    lv_draw_label(&layer, &dsc2, &c2);

    lv_canvas_finish_layer(canvas_, &layer);
}

void ClockDial::showConnecting() {
    clearCanvas();

    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);

    lv_draw_label_dsc_t dsc;
    lv_draw_label_dsc_init(&dsc);
    dsc.color = lv_color_make(100, 100, 255);
    dsc.font  = &lv_font_montserrat_28;
    dsc.text  = "Connecting...";
    dsc.align = LV_TEXT_ALIGN_CENTER;
    int fh = lv_font_get_line_height(dsc.font);
    lv_area_t c = { 0, CY - fh/2, W-1, CY + fh/2 };
    lv_draw_label(&layer, &dsc, &c);

    lv_canvas_finish_layer(canvas_, &layer);
}

void ClockDial::setAmbient(uint8_t category) {
    // Duty map: 0=100%, 1=70%, 2=40%, 3=30%
    // Actual backlight control is done in main.cpp via QspiDisplay::setBacklight()
    // This method is available for any canvas-level ambient adjustments
    (void)category;
}
