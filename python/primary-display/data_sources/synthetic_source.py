"""MGB Dash 2026 — Synthetic data source for display testing."""

import math
import time
import threading

from .base import DataSource
from vehicle_state import VehicleState
from common.python import can_ids
from common.python.can_log import LogLevel, LogRole, LogEvent


class SyntheticSource(DataSource):
    """Procedural test-data generator. Updates VehicleState directly
    (no CAN frame encoding) with time-varying realistic values.

    Scenarios: all_signals, idle, driving, charging
    """

    def __init__(self, state: VehicleState, scenario: str = "all_signals",
                 speed_factor: float = 1.0):
        super().__init__(state)
        self._scenario = scenario
        self._speed_factor = speed_factor
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="synthetic-source"
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    # ── Main loop ────────────────────────────────────────────────────

    def _run(self):
        t = 0.0
        dt = 0.1  # 10 Hz base rate
        while self._running:
            handler = getattr(self, f"_gen_{self._scenario}", self._gen_all_signals)
            handler(t)
            t += dt * self._speed_factor
            time.sleep(dt)

    # ── Scenarios ────────────────────────────────────────────────────

    def _gen_all_signals(self, t):
        speed = 30 + 15 * math.sin(t * 0.2)
        gear = self._gear_from_speed(speed)
        # Periodically hold the wrong gear to trigger shift advice
        cycle = int(t) % 40
        if 10 < cycle < 15 and gear > 1:
            gear -= 1   # one gear too low → upshift advice
        elif 25 < cycle < 30 and gear < 4:
            gear += 1   # one gear too high → downshift advice

        self._emit_leaf_motor(t, speed, gear)
        self._emit_leaf_battery(t)
        self._emit_leaf_charger(t, charging=True)
        self._emit_leaf_temps(t, alert_cycle=True)
        self._emit_leaf_vcm()
        self._emit_resolve(t)
        self._emit_body(t, speed_mph=speed, gear=gear)
        self._emit_gps(t)
        self._emit_heartbeats(t, drop_one=True)
        self._emit_log_alerts(t)

    def _gen_idle(self, t):
        self._emit_leaf_battery(t)
        self._emit_leaf_vcm()
        self._emit_body(t, speed_mph=0)
        self._emit_heartbeats(t)

    def _gen_driving(self, t):
        speed = 35 + 20 * math.sin(t * 0.15)
        gear = self._gear_from_speed(speed)
        self._emit_leaf_motor(t, speed, gear)
        self._emit_leaf_battery(t)
        self._emit_leaf_temps(t)
        self._emit_leaf_vcm()
        self._emit_resolve(t)
        self._emit_body(t, speed_mph=speed, gear=gear)
        self._emit_gps(t)
        self._emit_heartbeats(t)

    def _gen_charging(self, t):
        self._emit_leaf_battery(t)
        self._emit_leaf_charger(t, charging=True)
        self._emit_leaf_temps(t)
        self._emit_body(t, speed_mph=0)
        self._emit_heartbeats(t)

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _gear_from_speed(speed_mph: float) -> int:
        """Estimate gear from speed (simple threshold model)."""
        if speed_mph <= 1:
            return 0
        return min(4, max(1, int(speed_mph / 15) + 1))

    # ── Emitters ─────────────────────────────────────────────────────

    def _emit_leaf_motor(self, t, speed_mph: float = 30.0, gear: int = 2):
        # Compute realistic RPM from speed and gear ratio
        _GEAR_RATIOS = {1: 3.41, 2: 2.166, 3: 1.38, 4: 1.00}
        _DIFF = 3.909
        _TIRE = 26.5
        _RPM_BASE = 5280.0 * 12.0 / (60.0 * math.pi * _TIRE) * _DIFF

        if gear >= 1 and gear <= 4 and speed_mph > 0.5:
            expected_rpm = speed_mph * _RPM_BASE * _GEAR_RATIOS[gear]
            # Add drift that periodically crosses shift thresholds
            drift = 1200 * math.sin(t * 0.15)
            rpm = int(max(0, expected_rpm + drift))
        else:
            rpm = 0

        torque = 80 + 40 * math.sin(t * 0.25)
        self._state.update_signals({
            "motor_rpm": rpm,
            "available_torque_nm": round(torque, 1),
            "failsafe": 0,
        })
        self._state.update_raw(0x1DA, b"\x00" * 8)

    def _emit_leaf_battery(self, t):
        voltage = 360 + 10 * math.sin(t * 0.05)
        current = -30 + 25 * math.sin(t * 0.2)
        soc = 72 + 5 * math.sin(t * 0.01)
        self._state.update_signals({
            "battery_voltage_v":   round(voltage, 1),
            "battery_current_a":   round(current, 1),
            "soc_percent":         int(soc),
            "soc_precise_percent": round(soc + 0.37, 2),
            "gids":                int(200 + 20 * math.sin(t * 0.01)),
            "soh_percent":         92,
            "battery_temp_c":      round(28 + 3 * math.sin(t * 0.02), 1),
        })
        for aid in (0x1DB, 0x55B, 0x5BC, 0x5C0):
            self._state.update_raw(aid, b"\x00" * 8)

    def _emit_leaf_charger(self, t, charging: bool):
        power = (6.6 + 0.5 * math.sin(t * 0.1)) if charging else 0.0
        self._state.update_signals({"charge_power_kw": round(power, 2)})
        self._state.update_raw(0x1DC, b"\x00" * 8)

    def _emit_leaf_temps(self, t, alert_cycle: bool = False):
        # Periodically spike battery temp above 45C to trigger BATT TEMP HIGH alert
        if alert_cycle and 30 < (t % 60) < 40:
            batt_temp = 48.0
        else:
            batt_temp = round(28 + 3 * math.sin(t * 0.02), 1)
        self._state.update_signals({
            "motor_temp_c":    round(45 + 10 * math.sin(t * 0.03), 1),
            "igbt_temp_c":     round(42 + 8 * math.sin(t * 0.025), 1),
            "inverter_temp_c": round(38 + 6 * math.sin(t * 0.02), 1),
            "battery_temp_c":  batt_temp,
        })
        self._state.update_raw(0x55A, b"\x00" * 8)

    def _emit_leaf_vcm(self):
        self._state.update_signals({"main_relay_closed": True})
        self._state.update_raw(0x390, b"\x00" * 8)

    def _emit_resolve(self, t):
        gear_val = 2 if t > 5 else 0
        self._state.update_signals({
            "resolve_gear":                gear_val,
            "resolve_ignition_on":         True,
            "resolve_system_on":           True,
            "resolve_display_max_charge_on": False,
            "resolve_regen_strength":      int(50 + 30 * math.sin(t * 0.4)),
            "resolve_soc_percent":         int(72 + 5 * math.sin(t * 0.01)),
        })
        self._state.update_raw(0x539, b"\x00" * 8)

    def _emit_body(self, t, speed_mph: float, gear: int = None):
        flags = can_ids.BODY_FLAG_KEY_ON
        if speed_mph > 1 and math.sin(t * 0.5) > 0.7:
            flags |= can_ids.BODY_FLAG_BRAKE
        if speed_mph > 10 and math.sin(t * 0.3) > 0.8:
            flags |= can_ids.BODY_FLAG_REGEN
        if int(t) % 20 < 3:
            flags |= can_ids.BODY_FLAG_LEFT_TURN

        if gear is None:
            gear = self._gear_from_speed(speed_mph)

        self._state.update_signals({
            "key_on":          bool(flags & can_ids.BODY_FLAG_KEY_ON),
            "brake":           bool(flags & can_ids.BODY_FLAG_BRAKE),
            "regen":           bool(flags & can_ids.BODY_FLAG_REGEN),
            "fan":             False,
            "reverse":         False,
            "left_turn":       bool(flags & can_ids.BODY_FLAG_LEFT_TURN),
            "right_turn":      False,
            "hazard":          False,
            "body_speed_mph":  round(max(0.0, speed_mph), 1),
            "body_gear":       gear,
            "body_reverse":    False,
            "odometer_miles":  12345 + int(t * max(0.0, speed_mph) / 3600),
        })
        for aid in (0x710, 0x711, 0x712, 0x713):
            self._state.update_raw(aid, b"\x00" * 8)

    def _emit_gps(self, t):
        lat = 42.3601 + 0.001 * math.sin(t * 0.01)
        lon = -71.0589 + 0.001 * math.cos(t * 0.01)
        speed = 30 + 15 * math.sin(t * 0.2)
        self._state.update_signals({
            "gps_speed_mph":      round(max(0.0, speed), 1),
            "gps_latitude":       round(lat, 6),
            "gps_longitude":      round(lon, 6),
            "gps_elevation_m":    round(10 + 2 * math.sin(t * 0.005), 1),
            "gps_time_utc_s":     (t * 10) % 86400,
            "gps_date_days":      9551,   # ~2026-02-24
            "ambient_light_name": "DAYLIGHT",
            "ambient_light":      0,
            "gps_utc_offset_min": -300,   # EST (UTC-5)
        })
        for aid in range(0x720, 0x728):
            self._state.update_raw(aid, b"\x00" * 8)

    def _emit_heartbeats(self, t, drop_one: bool = False):
        counter = int(t) % 256
        for role_bytes in can_ids.ALL_ROLES:
            role = role_bytes.decode("ascii").strip()
            # Periodically stop updating GPS heartbeat to trigger HEARTBEAT LOST
            if drop_one and role == "GPS" and 45 < (t % 90) < 65:
                continue
            self._state.update_heartbeat(role, counter, 0)
        self._state.update_raw(0x700, b"\x00" * 8)

    def _emit_log_alerts(self, t):
        """Push synthetic CAN LOG alerts directly to the AlertManager."""
        mgr = self._state.alert_manager
        if mgr is None:
            return
        tick = int(t * 10)  # 10Hz ticks

        # Every ~8s: WARN from BODY — low voltage
        if tick % 80 == 0:
            mgr.push(LogRole.BODY, LogLevel.LOG_WARN,
                     LogEvent.LOW_VOLTAGE, "12V battery 11.2V")

        # Every ~15s: INFO from GPS
        if tick % 150 == 10:
            mgr.push(LogRole.GPS, LogLevel.LOG_INFO,
                     LogEvent.GPS_FIX_ACQUIRED, "3D fix 8 sats")

        # Every ~25s: ERROR from TEMP
        if tick % 250 == 20:
            mgr.push(LogRole.TEMP, LogLevel.LOG_ERROR,
                     LogEvent.OVERTEMP, "Inverter 92C")

        # Every ~40s: CRITICAL from BODY
        if tick % 400 == 30:
            mgr.push(LogRole.BODY, LogLevel.LOG_CRITICAL,
                     LogEvent.BUS_OFF, "CAN bus off")

        # Every ~12s: alternating upshift / downshift advice
        if tick % 120 == 50:
            mgr.push(LogRole.DASH, LogLevel.LOG_INFO,
                     LogEvent.GENERIC_INFO, "Upshift to gear 3")
        if tick % 120 == 110:
            mgr.push(LogRole.DASH, LogLevel.LOG_INFO,
                     LogEvent.GENERIC_INFO, "Downshift to gear 2")
