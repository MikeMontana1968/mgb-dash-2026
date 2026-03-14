/**
 * MGB Dash 2026 — GPS Display (ESP32-S3)
 *
 * Waveshare ESP32-S3-LCD-1.85 (360x360 round LCD, BLE 5.0, no CAN).
 * Receives GPS CAN frames via BLE from the Amps module (MGB-AMPS),
 * computes ephemeris, and renders a 24-hour clock dial with sun/moon arcs.
 *
 * Data flow: Pi 3B (GPS+CAN) -> CAN bus -> Amps ESP32 (BLE bridge) -> BLE -> here
 */

#include <Arduino.h>
#include <cstring>
#include <cmath>
#include "esp_log.h"
#include "lvgl.h"
#include "QspiDisplay.h"
#include "BleClient.h"
#include "ClockDial.h"
#include "Ephemeris.h"
#include "can_ids.h"

static const char* TAG = "GPS_DISP";

QspiDisplay display;
BleClient bleClient;
ClockDial clockDial;

// ── GPS data state (decoded from BLE-forwarded CAN frames) ──────────────
static double gpsSpeedMph        = 0.0;
static double gpsSecsSinceMidnight = -1.0;
static double gpsDaysSince2000   = -1.0;
static double gpsLat             = 0.0;
static double gpsLon             = 0.0;
static int16_t gpsUtcOffsetMin   = 0;
static uint8_t gpsAmbient        = 0;
static bool    gpsTimeValid      = false;
static bool    gpsDateValid      = false;
static bool    gpsPositionValid  = false;
static unsigned long lastGpsFrameMs = 0;

// ── Display state ───────────────────────────────────────────────────────
enum DispState { DISP_CONNECTING, DISP_WAITING, DISP_RUNNING, DISP_SIGNAL_LOST, DISP_DEMO };
static DispState dispState = DISP_CONNECTING;
static unsigned long waitStartMs = 0;
static unsigned long lastDisplayUpdateMs = 0;
static constexpr unsigned long DISPLAY_UPDATE_MS = 1000;  // 1 Hz refresh
static constexpr unsigned long GPS_TIMEOUT_MS    = 5000;  // 5s no frames = signal lost
static constexpr unsigned long BLE_DEMO_TIMEOUT_MS = 5000; // 5s no BLE = demo mode

// ── Demo mode defaults (Edison, NJ + build time) ────────────────────────
static constexpr double DEMO_LAT = 40.5187;
static constexpr double DEMO_LON = -74.4121;
static constexpr int16_t DEMO_UTC_OFFSET_MIN = -240;  // EDT

// Parse build date from VERSION_DATE (YMMDD format: e.g. "60311" = 2026-03-11)
static void getBuildDate(int& year, int& month, int& day) {
    const char* d = VERSION_DATE;
    int ymmdd = atoi(d);
    year  = 2020 + (ymmdd / 10000);
    month = (ymmdd / 100) % 100;
    day   = ymmdd % 100;
}

// ── Decode 64-bit double from 8-byte CAN data ──────────────────────────
static double decodeDouble(const uint8_t* data) {
    double val;
    memcpy(&val, data, sizeof(double));
    return val;
}

// ── Convert days since 2000-01-01 to y/m/d ──────────────────────────────
static void daysToDate(int totalDays, int& year, int& month, int& day) {
    // Days since 2000-01-01
    // Convert to days since Unix epoch (1970-01-01)
    int epochDays = totalDays + 10957;  // 2000-01-01 is day 10957 from 1970-01-01

    // Howard Hinnant's civil_from_days
    epochDays += 719468;
    int era = (epochDays >= 0 ? epochDays : epochDays - 146096) / 146097;
    int doe = epochDays - era * 146097;
    int yoe = (doe - doe/1460 + doe/36524 - doe/146096) / 365;
    int y   = yoe + era * 400;
    int doy = doe - (365*yoe + yoe/4 - yoe/100);
    int mp  = (5*doy + 2) / 153;
    int d   = doy - (153*mp + 2) / 5 + 1;
    int m   = mp + (mp < 10 ? 3 : -9);
    y += (m <= 2);

    year  = y;
    month = m;
    day   = d;
}

// ── Day of week (0=Sun, 1=Mon, ..., 6=Sat) ─────────────────────────────
static int dayOfWeek(int year, int month, int day) {
    // Tomohiko Sakamoto's algorithm
    static const int t[] = { 0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4 };
    int y = year;
    if (month < 3) y--;
    return (y + y/4 - y/100 + y/400 + t[month-1] + day) % 7;
}

// ── CAN frame callback (called from BleClient::update on main thread) ──
static void onCanFrame(const CanFrame& frame) {
    lastGpsFrameMs = millis();

    switch (frame.id) {
        case CAN_ID_GPS_SPEED:
            gpsSpeedMph = decodeDouble(frame.data);
            break;

        case CAN_ID_GPS_TIME:
            gpsSecsSinceMidnight = decodeDouble(frame.data);
            gpsTimeValid = (gpsSecsSinceMidnight >= 0);
            break;

        case CAN_ID_GPS_DATE:
            gpsDaysSince2000 = decodeDouble(frame.data);
            gpsDateValid = (gpsDaysSince2000 >= 0);
            break;

        case CAN_ID_GPS_LATITUDE:
            gpsLat = decodeDouble(frame.data);
            gpsPositionValid = true;
            break;

        case CAN_ID_GPS_LONGITUDE:
            gpsLon = decodeDouble(frame.data);
            break;

        case CAN_ID_GPS_AMBIENT_LIGHT:
            gpsAmbient = frame.data[0];
            break;

        case CAN_ID_GPS_UTC_OFFSET: {
            int16_t off;
            memcpy(&off, frame.data, sizeof(int16_t));
            gpsUtcOffsetMin = off;
            break;
        }

        case CAN_ID_BODY_STATE:
            // Could use body state flags for future features
            break;

        default:
            break;
    }
}

// ── Setup ───────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);

    char versionStr[48];
    snprintf(versionStr, sizeof(versionStr), "GPS_DISP v%d.%s.%s",
             VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    ESP_LOGI(TAG, "%s starting...", versionStr);

    // Initialize LVGL
    lv_init();
    lv_tick_set_cb([]() -> uint32_t { return (uint32_t)millis(); });

    // Initialize display hardware + LVGL driver
    if (!display.init()) {
        ESP_LOGE(TAG, "Display init failed!");
        return;
    }

    // Initialize clock dial renderer
    clockDial.init(lv_screen_active());
    clockDial.showWaiting(0);
    lv_timer_handler();  // flush initial screen

    // Initialize BLE client
    bleClient.init();
    bleClient.setOnFrame(onCanFrame);

    waitStartMs = millis();
    dispState = DISP_CONNECTING;

    ESP_LOGI(TAG, "Init complete — waiting for BLE connection (demo after %lus)",
             BLE_DEMO_TIMEOUT_MS / 1000);
}

// ── Main loop ───────────────────────────────────────────────────────────

void loop() {
    // LVGL tick
    lv_timer_handler();

    // BLE frame processing
    bleClient.update();

    unsigned long now = millis();

    // State machine (1 Hz updates)
    if (now - lastDisplayUpdateMs < DISPLAY_UPDATE_MS) return;
    lastDisplayUpdateMs = now;

    bool bleConnected = bleClient.isConnected();
    bool hasRecentFrames = (lastGpsFrameMs > 0) && (now - lastGpsFrameMs < GPS_TIMEOUT_MS);
    bool gpsReady = gpsTimeValid && gpsDateValid && gpsPositionValid;

    switch (dispState) {
        case DISP_CONNECTING: {
            int elapsed = (int)((now - waitStartMs) / 1000);
            if (bleConnected) {
                dispState = DISP_WAITING;
                waitStartMs = now;
                ESP_LOGI(TAG, "BLE connected, waiting for GPS data...");
            } else if (now - waitStartMs >= BLE_DEMO_TIMEOUT_MS) {
                dispState = DISP_DEMO;
                ESP_LOGI(TAG, "No BLE found — entering demo mode (Edison, NJ)");
            } else {
                clockDial.showWaiting(elapsed);
            }
            break;
        }

        case DISP_WAITING:
            if (!bleConnected) {
                dispState = DISP_CONNECTING;
                waitStartMs = now;
            } else if (gpsReady && hasRecentFrames) {
                dispState = DISP_RUNNING;
                ESP_LOGI(TAG, "GPS data valid, entering normal mode");
            } else {
                int elapsed = (int)((now - waitStartMs) / 1000);
                clockDial.showWaiting(elapsed);
            }
            break;

        case DISP_RUNNING:
            if (!bleConnected) {
                dispState = DISP_CONNECTING;
                clockDial.showConnecting();
            } else if (!hasRecentFrames) {
                dispState = DISP_SIGNAL_LOST;
                ESP_LOGW(TAG, "GPS signal lost");
            } else if (gpsReady) {
                // Convert UTC seconds-since-midnight + offset to local time
                int utcSecs = (int)gpsSecsSinceMidnight;
                int localSecs = utcSecs + gpsUtcOffsetMin * 60;

                // Handle day rollover
                int dayOffset = 0;
                if (localSecs < 0)      { localSecs += 86400; dayOffset = -1; }
                if (localSecs >= 86400) { localSecs -= 86400; dayOffset =  1; }

                int hour = localSecs / 3600;
                int minute = (localSecs % 3600) / 60;
                int second = localSecs % 60;

                int year, month, day;
                daysToDate((int)gpsDaysSince2000 + dayOffset, year, month, day);
                int dow = dayOfWeek(year, month, day);

                clockDial.setData(hour, minute, second,
                                  day, month, year, dow,
                                  gpsSpeedMph, gpsLat, gpsLon);

                // Backlight from ambient
                uint8_t dutyMap[] = { 100, 70, 40, 30 };
                uint8_t duty = (gpsAmbient < 4) ? dutyMap[gpsAmbient] : 100;
                display.setBacklight(duty);
            }
            break;

        case DISP_SIGNAL_LOST:
            if (!bleConnected) {
                dispState = DISP_CONNECTING;
                waitStartMs = now;
            } else if (hasRecentFrames && gpsReady) {
                dispState = DISP_RUNNING;
                ESP_LOGI(TAG, "GPS signal restored");
            } else {
                // Show last known time (approximate from millis)
                char timeBuf[8];
                int utcSecs = (int)gpsSecsSinceMidnight;
                int localSecs = utcSecs + gpsUtcOffsetMin * 60;
                // Add elapsed since last frame
                localSecs += (int)((now - lastGpsFrameMs) / 1000);
                if (localSecs < 0)      localSecs += 86400;
                if (localSecs >= 86400) localSecs -= 86400;
                int h12 = (localSecs / 3600) % 12;
                if (h12 == 0) h12 = 12;
                snprintf(timeBuf, sizeof(timeBuf), "%d:%02d",
                         h12, (localSecs % 3600) / 60);
                clockDial.showSignalLost(timeBuf);
            }
            break;

        case DISP_DEMO: {
            // If BLE connects while in demo, switch to live mode
            if (bleConnected) {
                dispState = DISP_WAITING;
                waitStartMs = now;
                ESP_LOGI(TAG, "BLE connected — leaving demo mode");
                break;
            }

            // Use build date + uptime as simulated time
            int demoYear, demoMonth, demoDay;
            getBuildDate(demoYear, demoMonth, demoDay);

            // Simulate time: start at noon + advance with uptime
            int simSecs = 12 * 3600 + (int)(now / 1000);
            simSecs %= 86400;
            int hour   = simSecs / 3600;
            int minute = (simSecs % 3600) / 60;
            int second = simSecs % 60;
            int dow = dayOfWeek(demoYear, demoMonth, demoDay);

            clockDial.setData(hour, minute, second,
                              demoDay, demoMonth, demoYear, dow,
                              0.0, DEMO_LAT, DEMO_LON);
            break;
        }
    }
}
