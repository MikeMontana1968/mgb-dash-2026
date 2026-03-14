#pragma once
/**
 * MGB Dash 2026 — Ephemeris (Sun/Moon Calculations)
 *
 * C++ port of python/gps-display/ephemeris.py (suncalcPy2-based).
 * Provides sunrise/sunset, moonrise/moonset, moon illumination,
 * and decimal-hour conversions.
 */

#include <cstdint>

namespace Ephemeris {

struct SunTimes {
    double rise;            // decimal hours (0-24)
    double set;
    double dawn;            // civil dawn (-6 deg)
    double dusk;
    double nauticalDawn;    // -12 deg
    double nauticalDusk;
};

struct MoonTimes {
    double rise;            // decimal hours, or -1 if no rise this day
    double set;             // decimal hours, or -1 if no set this day
    bool alwaysUp;
    bool alwaysDown;
};

struct MoonIllumination {
    double fraction;        // 0.0 - 1.0
    double phase;           // 0.0 - 1.0 (0=new, 0.5=full)
    double angle;           // radians
};

SunTimes getSunTimes(int year, int month, int day, double lat, double lng);

MoonTimes getMoonTimes(int year, int month, int day, double lat, double lng);

MoonIllumination getMoonIllumination(int year, int month, int day,
                                     int hour = 12, int minute = 0, int second = 0);

inline double timeToDecimalHours(int hour, int minute, int second = 0) {
    return hour + minute / 60.0 + second / 3600.0;
}

} // namespace Ephemeris
