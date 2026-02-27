"""MGB Dash 2026 — Driving context: three concentric arc gauges."""

import math
from typing import Optional

from .base import Context
from .alerts import AlertEvaluator, draw_alert
from rendering.colors import (
    ARC_SPEED, ARC_AMPS_DISCHARGE, ARC_AMPS_REGEN,
    ARC_RANGE, ARC_RANGE_OPTIMIST, ARC_RANGE_PESSIMIST,
    ARC_TRACK, TEXT_WHITE, TEXT_DIM,
)
from rendering.fonts import select_sans, select_mono
from rendering.cairo_helpers import draw_arc_gauge, draw_arc_fill, draw_text_centered

# Arc geometry (800x800, center 400,400)
_START_ANGLE = 8 * math.pi / 9     # 160deg — ~7:20 clock position
_SWEEP       = 11 * math.pi / 9    # 220deg

# Radius bands (inner_r, outer_r) — no gaps between arcs
_SPEED_BAND = (340, 385)   # outer
_AMPS_BAND  = (295, 340)   # middle (flush against speed)
_RANGE_BAND = (250, 295)   # inner (flush against amps)

# Scales
_SPEED_MAX = 100.0   # mph
_AMPS_MAX  = 300.0   # A (absolute value)
_RANGE_MAX = 80.0    # miles

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
    """Three concentric arc gauges: speed, amps, range.

    Range arc shows a three-shade uncertainty window around the current
    estimate: dark green (pessimistic) → medium green (current) → bright
    green (optimistic).  The solid fill runs up to the pessimistic edge;
    the window band sits at the leading edge of the fill.

    Bottom 140deg gap displays alert text.
    Tap anywhere toggles to diagnostics.
    """

    def __init__(self):
        self._alerts = AlertEvaluator()

    def render(self, ctx, state, width, height):
        cx, cy = width / 2, height / 2
        signals = state.get_all_signals()

        # Read values
        speed_sv   = signals.get("body_speed_mph")
        amps_sv    = signals.get("battery_current_a")
        soc_sv     = signals.get("soc_percent")
        voltage_sv = signals.get("battery_voltage_v")

        speed   = speed_sv.value if speed_sv else 0.0
        amps    = amps_sv.value if amps_sv else 0.0
        soc     = soc_sv.value if soc_sv else 0.0
        voltage = voltage_sv.value if voltage_sv else 360.0

        remaining_kwh = (soc / 100.0) * _BATTERY_KWH

        # ── Range estimates ───────────────────────────────────────────
        # Current estimate: use live power draw when driving, else baseline
        power_kw = abs(voltage * amps) / 1000.0
        if speed > 1.0 and power_kw > 0.1:
            live_eff = speed / power_kw  # mi/kWh instantaneous
            live_eff = max(1.5, min(6.0, live_eff))  # clamp sanity
        else:
            live_eff = _MI_PER_KWH_DEFAULT

        range_current = remaining_kwh * live_eff

        # Uncertainty window — band around current estimate
        range_pessimist = max(0.0, range_current - _RANGE_WINDOW_HALF)
        range_optimist  = min(_RANGE_MAX, range_current + _RANGE_WINDOW_HALF)

        # Fill ratios against scale
        ratio_pessimist = min(range_pessimist / _RANGE_MAX, 1.0)
        ratio_current   = min(range_current   / _RANGE_MAX, 1.0)
        ratio_optimist  = min(range_optimist  / _RANGE_MAX, 1.0)

        # Fill ratios for speed/amps
        speed_ratio = min(speed / _SPEED_MAX, 1.0) if _SPEED_MAX else 0
        amps_ratio  = min(abs(amps) / _AMPS_MAX, 1.0) if _AMPS_MAX else 0

        # Amps color: red when discharging (positive), green when regen (negative)
        amps_color = ARC_AMPS_REGEN if amps < 0 else ARC_AMPS_DISCHARGE

        # ── Draw speed + amps arcs ────────────────────────────────────
        draw_arc_gauge(ctx, cx, cy, *_SPEED_BAND, _START_ANGLE, _SWEEP,
                       speed_ratio, ARC_SPEED, ARC_TRACK)
        draw_arc_gauge(ctx, cx, cy, *_AMPS_BAND, _START_ANGLE, _SWEEP,
                       amps_ratio, amps_color, ARC_TRACK)

        # ── Draw range arc with uncertainty window ────────────────────
        # Gray track (full sweep)
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE, _SWEEP, ARC_TRACK)
        # Optimistic band (bright green) — extends past current estimate
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE,
                      _SWEEP * ratio_optimist, ARC_RANGE_OPTIMIST)
        # Current fill (medium green) — paints over optimistic up to current
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE,
                      _SWEEP * ratio_current, ARC_RANGE)
        # Pessimistic fill (dark green) — solid certain range
        draw_arc_fill(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE,
                      _SWEEP * ratio_pessimist, ARC_RANGE_PESSIMIST)

        # ── Labels at arc start (left side) — white text ─────────────
        self._draw_arc_label(ctx, cx, cy, _SPEED_BAND, "mph")
        self._draw_arc_label(ctx, cx, cy, _AMPS_BAND, "amps")
        self._draw_arc_label(ctx, cx, cy, _RANGE_BAND, "range")

        # ── Values past outermost colored edge — on the gray track ───
        self._draw_arc_value(ctx, cx, cy, _SPEED_BAND, speed_ratio,
                             f"{speed:.0f}")
        self._draw_arc_value(ctx, cx, cy, _AMPS_BAND, amps_ratio,
                             f"{abs(amps):.0f}")
        # Range value past the optimistic edge (outermost color)
        self._draw_arc_value(ctx, cx, cy, _RANGE_BAND, ratio_optimist,
                             f"{range_current:.0f}")

        # ── Center info ───────────────────────────────────────────────
        select_sans(ctx, 64, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        draw_text_centered(ctx, f"{speed:.0f}", cx, cy - 20)

        select_sans(ctx, 18)
        ctx.set_source_rgba(*TEXT_DIM)
        draw_text_centered(ctx, "MPH", cx, cy + 15)

        select_mono(ctx, 16)
        ctx.set_source_rgba(*TEXT_DIM)
        draw_text_centered(ctx, f"SOC {soc:.0f}%", cx, cy + 45)

        # ── Alerts in bottom gap ──────────────────────────────────────
        active_alerts = self._alerts.get_active_alerts(state)
        if active_alerts:
            draw_alert(ctx, active_alerts[0], cx, cy + 340)

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return "diagnostics"

    # ── Helpers ────────────────────────────────────────────────────────

    def _draw_arc_label(self, ctx, cx, cy, band, text):
        """Draw white label near the start of an arc (left side)."""
        mid_r = (band[0] + band[1]) / 2
        angle = _START_ANGLE - 0.06
        lx = cx + mid_r * math.cos(angle)
        ly = cy + mid_r * math.sin(angle)

        select_mono(ctx, 11)
        ctx.set_source_rgba(*TEXT_WHITE)
        ext = ctx.text_extents(text)
        ctx.move_to(lx - ext.width / 2, ly + ext.height / 2)
        ctx.show_text(text)

    def _draw_arc_value(self, ctx, cx, cy, band, fill_ratio, text):
        """Draw white value centered in the arc band, just past the colored fill on gray track."""
        mid_r = (band[0] + band[1]) / 2
        # Offset a few px forward so the text sits fully on the gray track
        angle_offset = 4.0 / mid_r  # radians for ~4px at this radius
        tip_angle = _START_ANGLE + _SWEEP * max(fill_ratio, 0.05) + angle_offset
        vx = cx + mid_r * math.cos(tip_angle)
        vy = cy + mid_r * math.sin(tip_angle)

        select_sans(ctx, 16, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        ext = ctx.text_extents(text)
        ctx.move_to(vx - ext.width / 2, vy + ext.height / 2)
        ctx.show_text(text)
