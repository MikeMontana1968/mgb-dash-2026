"""MGB Dash 2026 — Driving context: four concentric arc gauges."""

import math
from typing import Optional

from .base import Context
from .alerts import draw_alerts
from rendering.colors import (
    ARC_RPM, ARC_SPEED, ARC_AMPS_DISCHARGE, ARC_AMPS_REGEN,
    ARC_RANGE, ARC_RANGE_OPTIMIST, ARC_RANGE_PESSIMIST,
    ARC_TRACK, TEXT_WHITE, TEXT_DIM,
)
from rendering.fonts import select_sans, select_mono
from rendering.cairo_helpers import draw_arc_gauge, draw_arc_fill, draw_text_centered

# Arc geometry (800x800, center 400,400)
_START_ANGLE = 5 * math.pi / 6     # 150deg — 8 o'clock position
_SWEEP       = 4 * math.pi / 3     # 240deg — clockwise to 4 o'clock

# Radius bands (inner_r, outer_r) — 55px each, no gaps, outer→inner
_RPM_BAND   = (335, 390)   # outermost
_SPEED_BAND = (280, 335)
_RANGE_BAND = (225, 280)
_AMPS_BAND  = (170, 225)   # innermost

# Scales
_RPM_MAX   = 10000.0  # Leaf motor max RPM
_SPEED_MAX = 100.0     # mph
_AMPS_MAX  = 300.0     # A (absolute value)
_RANGE_MAX = 80.0      # miles

# Range efficiency heuristics — Leaf AZE0, 24 kWh usable
_BATTERY_KWH       = 24.0
_MI_PER_KWH_DEFAULT = 3.5   # baseline efficiency; adjusted by live power draw

# TODO: Replace fixed window with rolling heuristic — track a windowed
#   stddev of mi/kWh over the last N minutes of driving.  The window
#   half-width (in miles) would then be:  remaining_kwh * stddev_mi_per_kwh.
#   Until that's implemented, use a fixed ±8 mi window around the current
#   estimate (roughly ±15% at typical SOC).
_RANGE_WINDOW_HALF = 8.0    # miles — fixed default uncertainty band


class DrivingContext(Context):
    """Four concentric arc gauges: RPM, speed, range, amps.

    Arcs sweep 240deg from 8 o'clock to 4 o'clock (120deg bottom gap).
    Range arc shows a three-shade uncertainty window.
    Alerts are displayed centered inside the arcs.
    Tap anywhere toggles to diagnostics.
    """

    def __init__(self):
        pass

    def render(self, ctx, state, width, height):
        cx, cy = width / 2, height / 2
        signals = state.get_all_signals()

        # Read values
        rpm_sv     = signals.get("motor_rpm")
        speed_sv   = signals.get("body_speed_mph")
        amps_sv    = signals.get("battery_current_a")
        soc_sv     = signals.get("soc_percent")
        voltage_sv = signals.get("battery_voltage_v")

        rpm     = rpm_sv.value if rpm_sv else 0.0
        speed   = speed_sv.value if speed_sv else 0.0
        amps    = amps_sv.value if amps_sv else 0.0
        soc     = soc_sv.value if soc_sv else 0.0
        voltage = voltage_sv.value if voltage_sv else 360.0

        remaining_kwh = (soc / 100.0) * _BATTERY_KWH

        # ── Range estimates ───────────────────────────────────────────
        power_kw = abs(voltage * amps) / 1000.0
        if speed > 1.0 and power_kw > 0.1:
            live_eff = speed / power_kw
            live_eff = max(1.5, min(6.0, live_eff))
        else:
            live_eff = _MI_PER_KWH_DEFAULT

        range_current   = remaining_kwh * live_eff
        range_pessimist = max(0.0, range_current - _RANGE_WINDOW_HALF)
        range_optimist  = min(_RANGE_MAX, range_current + _RANGE_WINDOW_HALF)

        ratio_pessimist = min(range_pessimist / _RANGE_MAX, 1.0)
        ratio_current   = min(range_current   / _RANGE_MAX, 1.0)
        ratio_optimist  = min(range_optimist  / _RANGE_MAX, 1.0)

        # Fill ratios for rpm/speed/amps
        rpm_ratio   = min(abs(rpm) / _RPM_MAX, 1.0)
        speed_ratio = min(speed / _SPEED_MAX, 1.0)
        amps_ratio  = min(abs(amps) / _AMPS_MAX, 1.0)

        amps_color = ARC_AMPS_REGEN if amps < 0 else ARC_AMPS_DISCHARGE

        # ── Draw arcs (outer → inner) ────────────────────────────────
        draw_arc_gauge(ctx, cx, cy, *_RPM_BAND, _START_ANGLE, _SWEEP,
                       rpm_ratio, ARC_RPM, ARC_TRACK)
        draw_arc_gauge(ctx, cx, cy, *_SPEED_BAND, _START_ANGLE, _SWEEP,
                       speed_ratio, ARC_SPEED, ARC_TRACK)

        # Range arc with uncertainty window
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE, _SWEEP, ARC_TRACK)
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE,
                      _SWEEP * ratio_optimist, ARC_RANGE_OPTIMIST)
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE,
                      _SWEEP * ratio_current, ARC_RANGE)
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE,
                      _SWEEP * ratio_pessimist, ARC_RANGE_PESSIMIST)

        draw_arc_gauge(ctx, cx, cy, *_AMPS_BAND, _START_ANGLE, _SWEEP,
                       amps_ratio, amps_color, ARC_TRACK)

        # ── Labels at arc start (left side) ───────────────────────────
        self._draw_arc_label(ctx, cx, cy, _RPM_BAND, "rpm")
        self._draw_arc_label(ctx, cx, cy, _SPEED_BAND, "mph")
        self._draw_arc_label(ctx, cx, cy, _RANGE_BAND, "range")
        self._draw_arc_label(ctx, cx, cy, _AMPS_BAND, "amps")

        # ── Values past outermost colored edge ────────────────────────
        self._draw_arc_value(ctx, cx, cy, _RPM_BAND, rpm_ratio,
                             f"{round(abs(rpm), -2):.0f}")
        self._draw_arc_value(ctx, cx, cy, _SPEED_BAND, speed_ratio,
                             f"{speed:.0f}")
        self._draw_arc_value(ctx, cx, cy, _RANGE_BAND, ratio_optimist,
                             f"{range_current:.0f}")
        self._draw_arc_value(ctx, cx, cy, _AMPS_BAND, amps_ratio,
                             f"{abs(amps):.0f}")

        # ── Alerts (centered) ────────────────────────────────────────
        if state.alert_manager:
            alerts = state.alert_manager.get_display_alerts()
            # Stack alerts around center, offset upward so they feel centered
            alert_base_y = cy - (len(alerts) - 1) * 10.0
            draw_alerts(ctx, alerts, cx, alert_base_y)

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return "diagnostics"

    # ── Helpers ────────────────────────────────────────────────────────

    def _draw_arc_label(self, ctx, cx, cy, band, text):
        """Draw white label near the start of an arc (left side)."""
        mid_r = (band[0] + band[1]) / 2
        angle = _START_ANGLE - 0.06
        lx = cx + mid_r * math.cos(angle)
        ly = cy + mid_r * math.sin(angle)

        select_mono(ctx, 13)
        ctx.set_source_rgba(*TEXT_WHITE)
        ext = ctx.text_extents(text)
        ctx.move_to(lx - ext.width / 2, ly + ext.height / 2)
        ctx.show_text(text)

    def _draw_arc_value(self, ctx, cx, cy, band, fill_ratio, text):
        """Draw black value centered in the arc band, inside the colored fill."""
        mid_r = (band[0] + band[1]) / 2
        select_sans(ctx, 18, bold=True)
        ext = ctx.text_extents(text)
        # Place text center inside the fill, pulled back from the tip edge
        gap_px = ext.width / 2 + 10.0
        angle_offset = gap_px / mid_r
        tip_angle = _START_ANGLE + _SWEEP * max(fill_ratio, 0.05) - angle_offset
        vx = cx + mid_r * math.cos(tip_angle)
        vy = cy + mid_r * math.sin(tip_angle)

        ctx.set_source_rgba(0.0, 0.0, 0.0, 1.0)
        ctx.move_to(vx - ext.width / 2, vy + ext.height / 2)
        ctx.show_text(text)
