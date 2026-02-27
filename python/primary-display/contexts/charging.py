"""MGB Dash 2026 — Charging context: SOC arc + charge info."""

import math
from typing import Optional

from .base import Context
from .alerts import AlertEvaluator
from rendering.colors import ARC_RANGE, ARC_TRACK, TEXT_WHITE, TEXT_DIM, ALERT_CYAN
from rendering.fonts import select_sans, select_mono
from rendering.cairo_helpers import draw_arc_gauge, draw_text_centered

# Single SOC arc — 270deg sweep (gap at bottom)
_START_ANGLE = 3 * math.pi / 4    # 135deg — ~7:30 clock position
_SWEEP       = 3 * math.pi / 2    # 270deg
_INNER_R     = 290
_OUTER_R     = 340


class ChargingContext(Context):
    """SOC arc gauge with charge power and estimated time to full.

    Tap anywhere toggles to diagnostics.
    """

    def __init__(self):
        self._alerts = AlertEvaluator()

    def render(self, ctx, state, width, height):
        cx, cy = width / 2, height / 2
        signals = state.get_all_signals()

        soc_sv    = signals.get("soc_percent")
        charge_sv = signals.get("charge_power_kw")

        soc = soc_sv.value if soc_sv else 0
        charge_kw = charge_sv.value if charge_sv else 0.0
        fill_ratio = soc / 100.0

        # ── SOC arc ───────────────────────────────────────────────────
        draw_arc_gauge(ctx, cx, cy, _INNER_R, _OUTER_R,
                       _START_ANGLE, _SWEEP, fill_ratio, ARC_RANGE, ARC_TRACK)

        # ── Large SOC text ────────────────────────────────────────────
        select_sans(ctx, 80, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        draw_text_centered(ctx, f"{soc:.0f}%", cx, cy - 40)

        # ── "CHARGING" label ──────────────────────────────────────────
        select_sans(ctx, 20)
        ctx.set_source_rgba(*ALERT_CYAN)
        draw_text_centered(ctx, "CHARGING", cx, cy + 10)

        # ── Charge power ──────────────────────────────────────────────
        select_sans(ctx, 28, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        draw_text_centered(ctx, f"{charge_kw:.1f} kW", cx, cy + 55)

        # ── Estimated time to full ────────────────────────────────────
        remaining_pct = max(0.0, 100.0 - soc)
        if charge_kw > 0.1 and remaining_pct > 0:
            # 24 kWh usable battery (Leaf AZE0 ~24kWh)
            remaining_kwh = remaining_pct / 100.0 * 24.0
            hours = remaining_kwh / charge_kw
            h = int(hours)
            m = int((hours - h) * 60)
            eta_str = f"{h}h {m:02d}m to full"
        elif remaining_pct <= 0:
            eta_str = "FULL"
        else:
            eta_str = "-- to full"

        select_mono(ctx, 16)
        ctx.set_source_rgba(*TEXT_DIM)
        draw_text_centered(ctx, eta_str, cx, cy + 95)

        # ── Alerts ────────────────────────────────────────────────────
        active_alerts = self._alerts.get_active_alerts(state)
        if active_alerts:
            alert = active_alerts[0]
            select_sans(ctx, 16, bold=True)
            ctx.set_source_rgba(*alert.color)
            draw_text_centered(ctx, alert.message, cx, cy + 340)

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return "diagnostics"
