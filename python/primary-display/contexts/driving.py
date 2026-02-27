"""MGB Dash 2026 — Driving context: three concentric arc gauges."""

import math
from typing import Optional

from .base import Context
from .alerts import AlertEvaluator
from rendering.colors import (
    ARC_SPEED, ARC_AMPS_DISCHARGE, ARC_AMPS_REGEN, ARC_RANGE,
    ARC_TRACK, TEXT_WHITE, TEXT_DIM,
)
from rendering.fonts import select_sans, select_mono
from rendering.cairo_helpers import draw_arc_gauge, draw_text_centered

# Arc geometry (800x800, center 400,400)
_START_ANGLE = 8 * math.pi / 9     # 160deg — ~7:20 clock position
_SWEEP       = 11 * math.pi / 9    # 220deg

# Radius bands (inner_r, outer_r)
_SPEED_BAND = (340, 385)   # outer
_AMPS_BAND  = (285, 330)   # middle
_RANGE_BAND = (230, 275)   # inner

# Scales
_SPEED_MAX = 100.0   # mph
_AMPS_MAX  = 300.0   # A (absolute value)
_RANGE_MAX = 80.0    # miles


class DrivingContext(Context):
    """Three concentric arc gauges: speed, amps, range.

    Bottom 140deg gap displays alert text.
    Tap anywhere toggles to diagnostics.
    """

    def __init__(self):
        self._alerts = AlertEvaluator()

    def render(self, ctx, state, width, height):
        cx, cy = width / 2, height / 2
        signals = state.get_all_signals()

        # Read values
        speed_sv = signals.get("body_speed_mph")
        amps_sv  = signals.get("battery_current_a")
        soc_sv   = signals.get("soc_percent")

        speed = speed_sv.value if speed_sv else 0.0
        amps  = amps_sv.value if amps_sv else 0.0
        soc   = soc_sv.value if soc_sv else 0.0

        # Range estimate: SOC% * 0.8 mi
        est_range = soc * 0.8

        # Fill ratios
        speed_ratio = min(speed / _SPEED_MAX, 1.0) if _SPEED_MAX else 0
        amps_ratio  = min(abs(amps) / _AMPS_MAX, 1.0) if _AMPS_MAX else 0
        range_ratio = min(est_range / _RANGE_MAX, 1.0) if _RANGE_MAX else 0

        # Amps color: red when discharging (positive), green when regen (negative)
        amps_color = ARC_AMPS_REGEN if amps < 0 else ARC_AMPS_DISCHARGE

        # ── Draw arcs ─────────────────────────────────────────────────
        draw_arc_gauge(ctx, cx, cy, *_SPEED_BAND, _START_ANGLE, _SWEEP,
                       speed_ratio, ARC_SPEED, ARC_TRACK)
        draw_arc_gauge(ctx, cx, cy, *_AMPS_BAND, _START_ANGLE, _SWEEP,
                       amps_ratio, amps_color, ARC_TRACK)
        draw_arc_gauge(ctx, cx, cy, *_RANGE_BAND, _START_ANGLE, _SWEEP,
                       range_ratio, ARC_RANGE, ARC_TRACK)

        # ── Labels at arc start (left side) ───────────────────────────
        self._draw_arc_label(ctx, cx, cy, _SPEED_BAND, "mph", ARC_SPEED)
        self._draw_arc_label(ctx, cx, cy, _AMPS_BAND, "amps", amps_color)
        self._draw_arc_label(ctx, cx, cy, _RANGE_BAND, "range", ARC_RANGE)

        # ── Values at arc tip ─────────────────────────────────────────
        self._draw_arc_value(ctx, cx, cy, _SPEED_BAND, speed_ratio,
                             f"{speed:.0f}", ARC_SPEED)
        amps_str = f"{abs(amps):.0f}"
        self._draw_arc_value(ctx, cx, cy, _AMPS_BAND, amps_ratio,
                             amps_str, amps_color)
        self._draw_arc_value(ctx, cx, cy, _RANGE_BAND, range_ratio,
                             f"{est_range:.0f}", ARC_RANGE)

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
            alert = active_alerts[0]  # show highest priority
            select_sans(ctx, 16, bold=True)
            ctx.set_source_rgba(*alert.color)
            draw_text_centered(ctx, alert.message, cx, cy + 340)

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return "diagnostics"

    # ── Helpers ────────────────────────────────────────────────────────

    def _draw_arc_label(self, ctx, cx, cy, band, text, color):
        """Draw label near the start of an arc (left side)."""
        mid_r = (band[0] + band[1]) / 2
        # Position just past the start angle, offset outward for readability
        angle = _START_ANGLE - 0.06
        lx = cx + mid_r * math.cos(angle)
        ly = cy + mid_r * math.sin(angle)

        select_mono(ctx, 11)
        ctx.set_source_rgba(*color)
        ext = ctx.text_extents(text)
        ctx.move_to(lx - ext.width / 2, ly + ext.height / 2)
        ctx.show_text(text)

    def _draw_arc_value(self, ctx, cx, cy, band, fill_ratio, text, color):
        """Draw value at the tip of the filled arc."""
        mid_r = (band[0] + band[1]) / 2
        tip_angle = _START_ANGLE + _SWEEP * max(fill_ratio, 0.05)
        vx = cx + mid_r * math.cos(tip_angle)
        vy = cy + mid_r * math.sin(tip_angle)

        select_sans(ctx, 16, bold=True)
        ctx.set_source_rgba(*color)
        ext = ctx.text_extents(text)
        ctx.move_to(vx - ext.width / 2, vy + ext.height / 2)
        ctx.show_text(text)
