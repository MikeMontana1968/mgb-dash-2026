"""MGB Dash 2026 — System clock sync from GPS CAN data.

Sets the primary display Pi's system clock from GPS_TIME + GPS_DATE
when drift exceeds 5 seconds. Also sets the timezone from GPS_UTC_OFFSET.

Only runs on Linux (the Pi). Requires passwordless sudo for date and
timedatectl — see pi-setup/primary-display.sh.
"""

import platform
import subprocess
import time
from datetime import datetime, date, timedelta, timezone

import logging
logger = logging.getLogger("primary-display.clock_sync")

# Rate limit: at most once per 60 seconds
_last_sync_time = 0.0
_SYNC_INTERVAL_S = 60.0

# Track current offset to detect changes
_current_offset_min = None

# Staleness threshold
_MAX_AGE_S = 10.0

# Drift threshold
_DRIFT_THRESHOLD_S = 5.0

# GPS epoch
_GPS_EPOCH = date(2000, 1, 1)


def try_sync_clock(state):
    """Attempt to sync system clock from GPS CAN signals.

    Reads gps_time_utc_s, gps_date_days, gps_utc_offset_min from state.
    Skips if any signal is missing or stale (>10s).
    Rate-limited to at most once per 60 seconds.
    Only runs on Linux.
    """
    if platform.system() != "Linux":
        return

    global _last_sync_time, _current_offset_min

    now_mono = time.monotonic()
    if now_mono - _last_sync_time < _SYNC_INTERVAL_S:
        return

    try:
        signals = state.get_all_signals()

        # Check required signals exist
        time_sig = signals.get("gps_time_utc_s")
        date_sig = signals.get("gps_date_days")
        offset_sig = signals.get("gps_utc_offset_min")
        if time_sig is None or date_sig is None or offset_sig is None:
            return

        # Check staleness
        if (time_sig.age_seconds > _MAX_AGE_S
                or date_sig.age_seconds > _MAX_AGE_S
                or offset_sig.age_seconds > _MAX_AGE_S):
            return

        utc_secs = time_sig.value        # float, seconds since midnight UTC
        utc_days = date_sig.value         # float, days since 2000-01-01
        offset_min = int(offset_sig.value)  # int, UTC offset in minutes

        # Reconstruct UTC datetime
        gps_date = _GPS_EPOCH + timedelta(days=int(utc_days))
        hours = int(utc_secs) // 3600
        minutes = (int(utc_secs) % 3600) // 60
        seconds = int(utc_secs) % 60
        gps_utc = datetime(gps_date.year, gps_date.month, gps_date.day,
                           hours, minutes, seconds, tzinfo=timezone.utc)

        # Compare with system clock
        system_utc = datetime.now(timezone.utc)
        drift = abs((gps_utc - system_utc).total_seconds())

        if drift > _DRIFT_THRESHOLD_S:
            # Set system clock: date -u -s "YYYY-MM-DD HH:MM:SS"
            date_str = gps_utc.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Clock drift {drift:.1f}s > {_DRIFT_THRESHOLD_S}s, "
                        f"setting system clock to UTC {date_str}")
            subprocess.run(
                ["sudo", "date", "-u", "-s", date_str],
                capture_output=True, timeout=5,
            )

        # Set timezone if offset changed
        if offset_min != _current_offset_min:
            _set_timezone_from_offset(offset_min)
            _current_offset_min = offset_min

        _last_sync_time = now_mono

    except Exception as e:
        logger.error(f"Clock sync error: {e}")
        _last_sync_time = now_mono  # don't retry immediately on error


def _set_timezone_from_offset(offset_min):
    """Set system timezone using timedatectl.

    Uses POSIX Etc/GMT±N zones where the sign is inverted:
    UTC-5 (EST) → Etc/GMT+5, UTC+9 (JST) → Etc/GMT-9.
    """
    offset_hours = offset_min // 60
    offset_remainder = offset_min % 60

    if offset_remainder != 0:
        # Non-whole-hour offsets (e.g. India UTC+5:30) can't use Etc/GMT±N.
        # Fall back to a fixed-offset approach — log and skip.
        logger.warning(f"UTC offset {offset_min}min is not a whole hour, "
                       f"cannot set Etc/GMT timezone")
        return

    # POSIX sign inversion: UTC-5 → Etc/GMT+5
    posix_sign = -offset_hours
    if posix_sign == 0:
        tz_name = "Etc/GMT"
    elif posix_sign > 0:
        tz_name = f"Etc/GMT+{posix_sign}"
    else:
        tz_name = f"Etc/GMT{posix_sign}"

    logger.info(f"Setting timezone to {tz_name} (UTC offset {offset_min}min)")
    try:
        subprocess.run(
            ["sudo", "timedatectl", "set-timezone", tz_name],
            capture_output=True, timeout=5,
        )
    except Exception as e:
        logger.error(f"Failed to set timezone: {e}")
