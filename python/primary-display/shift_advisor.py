"""MGB Dash 2026 — Gear shift advisor.

Evaluates motor RPM vs speed for the current gear and pushes INFO-level
alerts when an upshift or downshift would be beneficial.

Uses the MGB 4-speed gearbox ratios (same constants as esp32/platformio.ini).
"""

import time

from common.python.can_log import LogLevel, LogRole, LogEvent

# MGB 4-speed gearbox ratios
GEAR_RATIOS = {1: 3.41, 2: 2.166, 3: 1.38, 4: 1.00}
DIFF_RATIO = 3.909
TIRE_DIAMETER_IN = 26.5

# Derived constant: converts mph to wheel RPM, then through diff
# = (5280 ft/mi * 12 in/ft) / (60 min/hr * pi * tire_diameter_in)  * diff_ratio
_RPM_PER_MPH_BASE = (
    5280.0 * 12.0 / (60.0 * 3.14159265 * TIRE_DIAMETER_IN) * DIFF_RATIO
)

# Shift thresholds (motor RPM)
UPSHIFT_RPM = 5500
DOWNSHIFT_RPM = 2000
TARGET_MIN_RPM = 1500   # don't suggest shift if target gear RPM < this
TARGET_MAX_RPM = 7000   # don't suggest shift if target gear RPM > this

# Cooldown between shift suggestions
SHIFT_COOLDOWN = 8.0    # seconds

# Minimum speed to evaluate shifts
MIN_SPEED_MPH = 3.0


class ShiftAdvisor:
    """Evaluates RPM vs speed/gear and pushes shift alerts."""

    def __init__(self):
        self._last_alert_time = 0.0

    def evaluate(self, state):
        """Check if a gear shift should be recommended.  Called each frame."""
        mgr = state.alert_manager
        if mgr is None:
            return

        now = time.monotonic()
        if (now - self._last_alert_time) < SHIFT_COOLDOWN:
            return

        signals = state.get_all_signals()
        rpm_sv = signals.get("motor_rpm")
        speed_sv = signals.get("body_speed_mph")
        gear_sv = signals.get("body_gear")

        if not (rpm_sv and speed_sv and gear_sv):
            return

        rpm = rpm_sv.value
        speed = speed_sv.value
        gear = int(gear_sv.value)

        if speed < MIN_SPEED_MPH or gear < 1 or gear > 4:
            return

        # ── Upshift ─────────────────────────────────────────────────
        if gear < 4 and rpm > UPSHIFT_RPM:
            target = gear + 1
            target_rpm = speed * _RPM_PER_MPH_BASE * GEAR_RATIOS[target]
            if target_rpm >= TARGET_MIN_RPM:
                mgr.push(LogRole.DASH, LogLevel.LOG_INFO,
                         LogEvent.GENERIC_INFO,
                         f"Upshift to gear {target}")
                self._last_alert_time = now
                return

        # ── Downshift ───────────────────────────────────────────────
        if gear > 1 and rpm < DOWNSHIFT_RPM:
            target = gear - 1
            target_rpm = speed * _RPM_PER_MPH_BASE * GEAR_RATIOS[target]
            if target_rpm <= TARGET_MAX_RPM:
                mgr.push(LogRole.DASH, LogLevel.LOG_INFO,
                         LogEvent.GENERIC_INFO,
                         f"Downshift to gear {target}")
                self._last_alert_time = now
                return

    @staticmethod
    def expected_rpm(speed_mph: float, gear: int) -> float:
        """Compute expected motor RPM for a given speed and gear."""
        if gear not in GEAR_RATIOS:
            return 0.0
        return speed_mph * _RPM_PER_MPH_BASE * GEAR_RATIOS[gear]
