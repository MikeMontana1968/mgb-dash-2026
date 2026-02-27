"""MGB Dash 2026 — Driving context: three concentric arc gauges."""

import math
from typing import Optional

from .base import Context
from .alerts import AlertEvaluator, draw_alert
from rendering.colors import (
    ARC_SPEED, ARC_AMPS_DISCHARGE, ARC_AMPS_REGEN, ARC_RANGE,
    ARC_TRACK, TEXT_WHITE, TEXT_DIM,
)
from rendering.fonts import select_sans, select_mono
from rendering.cairo_helpers import draw_arc_gauge, draw_text_centered

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

        # ── Labels at arc start (left side) — white text ─────────────
        self._draw_arc_label(ctx, cx, cy, _SPEED_BAND, "mph")
        self._draw_arc_label(ctx, cx, cy, _AMPS_BAND, "amps")
        self._draw_arc_label(ctx, cx, cy, _RANGE_BAND, "range")

        # ── Values at arc tip — white text ───────────────────────────
        self._draw_arc_value(ctx, cx, cy, _SPEED_BAND, speed_ratio,
                             f"{speed:.0f}")
        amps_str = f"{abs(amps):.0f}"
        self._draw_arc_value(ctx, cx, cy, _AMPS_BAND, amps_ratio,
                             amps_str)
        self._draw_arc_value(ctx, cx, cy, _RANGE_BAND, range_ratio,
                             f"{est_range:.0f}")

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
        """Draw white value centered in the arc band, a few px past the fill tip on the gray track."""
        mid_r = (band[0] + band[1]) / 2
        # Offset ~4px forward along the arc so the text sits on the gray track
        angle_offset = 4.0 / mid_r  # radians for ~4px at this radius
        tip_angle = _START_ANGLE + _SWEEP * max(fill_ratio, 0.05) + angle_offset
        vx = cx + mid_r * math.cos(tip_angle)
        vy = cy + mid_r * math.sin(tip_angle)

        select_sans(ctx, 16, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        ext = ctx.text_extents(text)
        ctx.move_to(vx - ext.width / 2, vy + ext.height / 2)
        ctx.show_text(text)
