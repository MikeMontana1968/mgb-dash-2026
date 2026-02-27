"""MGB Dash 2026 — Idle context: parked/key-on display."""

import time
from typing import Optional

from .base import Context
from .alerts import AlertEvaluator, draw_alert
from rendering.colors import TEXT_WHITE, TEXT_DIM, ARC_RANGE
from rendering.fonts import select_sans, select_mono
from rendering.cairo_helpers import draw_text_centered


class IdleContext(Context):
    """Large SOC%, range estimate, elapsed time, odometer.

    Shown when vehicle is stationary with key on.
    Tap anywhere toggles to diagnostics.
    """

    def __init__(self):
        self._key_on_time: float | None = None
        self._alerts = AlertEvaluator()

    def render(self, ctx, state, width, height):
        cx, cy = width / 2, height / 2
        signals = state.get_all_signals()

        soc_sv   = signals.get("soc_percent")
        odo_sv   = signals.get("odometer_miles")
        key_sv   = signals.get("key_on")

        soc = soc_sv.value if soc_sv else 0
        odo = odo_sv.value if odo_sv else 0
        est_range = soc * 0.8

        # Track key-on elapsed time
        if key_sv and key_sv.value and self._key_on_time is None:
            self._key_on_time = time.monotonic()

        # ── Large SOC ─────────────────────────────────────────────────
        select_sans(ctx, 96, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        draw_text_centered(ctx, f"{soc:.0f}%", cx, cy - 60)

        # ── Range ─────────────────────────────────────────────────────
        select_sans(ctx, 28)
        ctx.set_source_rgba(*ARC_RANGE)
        draw_text_centered(ctx, f"{est_range:.0f} mi range", cx, cy + 10)

        # ── Elapsed time ──────────────────────────────────────────────
        if self._key_on_time is not None:
            elapsed = time.monotonic() - self._key_on_time
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            select_mono(ctx, 18)
            ctx.set_source_rgba(*TEXT_DIM)
            draw_text_centered(ctx, f"ON {mins:02d}:{secs:02d}", cx, cy + 60)

        # ── Odometer ──────────────────────────────────────────────────
        select_mono(ctx, 16)
        ctx.set_source_rgba(*TEXT_DIM)
        draw_text_centered(ctx, f"ODO {odo:,.0f} mi", cx, cy + 100)

        # ── Alerts ────────────────────────────────────────────────────
        active_alerts = self._alerts.get_active_alerts(state)
        if active_alerts:
            draw_alert(ctx, active_alerts[0], cx, cy + 340)

    def on_enter(self, state):
        if self._key_on_time is None:
            self._key_on_time = time.monotonic()

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return "diagnostics"
