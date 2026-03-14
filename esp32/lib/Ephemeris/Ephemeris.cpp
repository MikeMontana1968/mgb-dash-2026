#include "Ephemeris.h"
#include <cmath>

namespace Ephemeris {

// ── Constants (matching Python ephemeris.py) ────────────────────────────
static constexpr double PI    = 3.14159265358979323846;
static constexpr double rad   = PI / 180.0;
static constexpr double e     = rad * 23.4397;   // obliquity of the Earth
static constexpr double J1970 = 2440588.0;
static constexpr double J2000 = 2451545.0;
static constexpr double J0    = 0.0009;

// Sun time angle thresholds (degrees)
static constexpr double ANGLE_RISE_SET  = -0.833;
static constexpr double ANGLE_DAWN_DUSK = -6.0;
static constexpr double ANGLE_NAUTICAL  = -12.0;

// ── Julian date helpers ─────────────────────────────────────────────────

// Days since Unix epoch (1970-01-01) — Howard Hinnant's algorithm
static int daysSinceEpoch(int y, int m, int d) {
    y -= (m <= 2);
    int era = (y >= 0 ? y : y - 399) / 400;
    int yoe = y - era * 400;
    int doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + doe - 719468;
}

// Calendar date/time (UTC) to Julian days since J2000
static double toDays(int y, int mo, int d, int h = 12, int mi = 0, int s = 0) {
    double epochSec = daysSinceEpoch(y, mo, d) * 86400.0
                    + h * 3600.0 + mi * 60.0 + s;
    double jd = epochSec / 86400.0 - 0.5 + J1970;
    return jd - J2000;
}

// Julian date to decimal hours (time-of-day portion only)
static double fromJulianToHours(double j) {
    double epochSec = (j + 0.5 - J1970) * 86400.0;
    double days = epochSec / 86400.0;
    double frac = days - floor(days);
    return frac * 24.0;
}

// ── Trigonometric helpers ───────────────────────────────────────────────

static double rightAscension(double l, double b) {
    return atan2(sin(l) * cos(e) - tan(b) * sin(e), cos(l));
}

static double declinationCalc(double l, double b) {
    return asin(sin(b) * cos(e) + cos(b) * sin(e) * sin(l));
}

static double azimuthCalc(double H, double phi, double dec) {
    return atan2(sin(H), cos(H) * sin(phi) - tan(dec) * cos(phi));
}

static double altitudeCalc(double H, double phi, double dec) {
    return asin(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(H));
}

static double siderealTime(double d, double lw) {
    return rad * (280.16 + 360.9856235 * d) - lw;
}

static double solarMeanAnomaly(double d) {
    return rad * (357.5291 + 0.98560028 * d);
}

static double eclipticLongitude(double M) {
    double C = rad * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M));
    double P = rad * 102.9372;  // perihelion of the Earth
    return M + C + P + PI;
}

struct Coords { double dec; double ra; };

static Coords sunCoords(double d) {
    double M = solarMeanAnomaly(d);
    double L = eclipticLongitude(M);
    return { declinationCalc(L, 0), rightAscension(L, 0) };
}

struct MoonCoords_ { double ra; double dec; double dist; };

static MoonCoords_ moonCoordsCalc(double d) {
    double L = rad * (218.316 + 13.176396 * d);
    double M = rad * (134.963 + 13.064993 * d);
    double F = rad * (93.272  + 13.229350 * d);

    double l  = L + rad * 6.289 * sin(M);
    double b  = rad * 5.128 * sin(F);
    double dt = 385001.0 - 20905.0 * cos(M);

    return { rightAscension(l, b), declinationCalc(l, b), dt };
}

// ── Solar calculations ──────────────────────────────────────────────────

static double julianCycle(double d, double lw) {
    return round(d - J0 - lw / (2.0 * PI));
}

static double approxTransit(double Ht, double lw, double n) {
    return J0 + (Ht + lw) / (2.0 * PI) + n;
}

static double solarTransitJ(double ds, double M, double L) {
    return J2000 + ds + 0.0053 * sin(M) - 0.0069 * sin(2.0 * L);
}

static double hourAngleCalc(double h, double phi, double d) {
    double arg = (sin(h) - sin(phi) * sin(d)) / (cos(phi) * cos(d));
    // Clamp to [-1,1] — Python version raises ValueError, we clamp instead
    if (arg > 1.0)  arg = 1.0;
    if (arg < -1.0) arg = -1.0;
    return acos(arg);
}

static double getSetJ(double h, double lw, double phi, double dec,
                       double n, double M, double L) {
    double w = hourAngleCalc(h, phi, dec);
    double a = approxTransit(w, lw, n);
    return solarTransitJ(a, M, L);
}

// ── Moon position (for getMoonTimes iteration) ──────────────────────────

static double getMoonAltitude(int y, int mo, int d, double hours,
                              double lat, double lng) {
    int h  = (int)hours;
    int mi = (int)((hours - h) * 60.0);
    int s  = (int)(((hours - h) * 60.0 - mi) * 60.0);

    double lw  = rad * -lng;
    double phi = rad * lat;
    double dd  = toDays(y, mo, d, h, mi, s);

    MoonCoords_ c = moonCoordsCalc(dd);
    double H   = siderealTime(dd, lw) - c.ra;
    double alt = altitudeCalc(H, phi, c.dec);

    // Refraction correction
    alt = alt + rad * 0.017 / tan(alt + rad * 10.26 / (alt + rad * 5.10));
    return alt;
}

// ── Public API ──────────────────────────────────────────────────────────

SunTimes getSunTimes(int year, int month, int day, double lat, double lng) {
    double lw  = rad * -lng;
    double phi = rad * lat;

    double d  = toDays(year, month, day);
    double n  = julianCycle(d, lw);
    double ds = approxTransit(0, lw, n);

    double M   = solarMeanAnomaly(ds);
    double L   = eclipticLongitude(M);
    double dec = declinationCalc(L, 0);
    double Jnoon = solarTransitJ(ds, M, L);

    SunTimes result;

    // Rise/set (-0.833 deg)
    double Jset  = getSetJ(ANGLE_RISE_SET * rad, lw, phi, dec, n, M, L);
    double Jrise = Jnoon - (Jset - Jnoon);
    result.rise = fromJulianToHours(Jrise);
    result.set  = fromJulianToHours(Jset);

    // Civil dawn/dusk (-6 deg)
    Jset  = getSetJ(ANGLE_DAWN_DUSK * rad, lw, phi, dec, n, M, L);
    Jrise = Jnoon - (Jset - Jnoon);
    result.dawn = fromJulianToHours(Jrise);
    result.dusk = fromJulianToHours(Jset);

    // Nautical dawn/dusk (-12 deg)
    Jset  = getSetJ(ANGLE_NAUTICAL * rad, lw, phi, dec, n, M, L);
    Jrise = Jnoon - (Jset - Jnoon);
    result.nauticalDawn = fromJulianToHours(Jrise);
    result.nauticalDusk = fromJulianToHours(Jset);

    return result;
}

MoonTimes getMoonTimes(int year, int month, int day, double lat, double lng) {
    double hc = 0.133 * rad;

    double h0 = getMoonAltitude(year, month, day, 0.0, lat, lng) - hc;

    double riseHours = -1.0;
    double setHours  = -1.0;
    double ye = 0.0;

    for (int i = 1; i <= 24; i += 2) {
        double h1 = getMoonAltitude(year, month, day, (double)i, lat, lng) - hc;
        double h2 = getMoonAltitude(year, month, day, (double)(i + 1), lat, lng) - hc;

        double a  = (h0 + h2) / 2.0 - h1;
        double b  = (h2 - h0) / 2.0;
        double xe = -b / (2.0 * a);
        ye = (a * xe + b) * xe + h1;
        double d  = b * b - 4.0 * a * h1;

        int roots = 0;
        double x1 = 0.0, x2 = 0.0;

        if (d >= 0) {
            double dx = sqrt(d) / (fabs(a) * 2.0);
            x1 = xe - dx;
            x2 = xe + dx;
            if (fabs(x1) <= 1.0) roots++;
            if (fabs(x2) <= 1.0) roots++;
            if (x1 < -1.0) x1 = x2;
        }

        if (roots == 1) {
            if (h0 < 0)
                riseHours = i + x1;
            else
                setHours = i + x1;
        } else if (roots == 2) {
            riseHours = i + (ye < 0 ? x2 : x1);
            setHours  = i + (ye < 0 ? x1 : x2);
        }

        if (riseHours >= 0 && setHours >= 0) break;
        h0 = h2;
    }

    MoonTimes result;
    result.rise       = riseHours;
    result.set        = setHours;
    result.alwaysUp   = (riseHours < 0 && setHours < 0 && ye > 0);
    result.alwaysDown = (riseHours < 0 && setHours < 0 && ye <= 0);
    return result;
}

MoonIllumination getMoonIllumination(int year, int month, int day,
                                     int hour, int minute, int second) {
    double d = toDays(year, month, day, hour, minute, second);
    Coords s   = sunCoords(d);
    MoonCoords_ m = moonCoordsCalc(d);

    static constexpr double sdist = 149598000.0;  // Earth-Sun distance km
    double phi = acos(sin(s.dec) * sin(m.dec)
               + cos(s.dec) * cos(m.dec) * cos(s.ra - m.ra));
    double inc = atan2(sdist * sin(phi), m.dist - sdist * cos(phi));
    double angle = atan2(
        cos(s.dec) * sin(s.ra - m.ra),
        sin(s.dec) * cos(m.dec) - cos(s.dec) * sin(m.dec) * cos(s.ra - m.ra)
    );

    MoonIllumination result;
    result.fraction = (1.0 + cos(inc)) / 2.0;
    result.phase    = 0.5 + 0.5 * inc * (angle < 0 ? -1.0 : 1.0) / PI;
    result.angle    = angle;
    return result;
}

} // namespace Ephemeris
