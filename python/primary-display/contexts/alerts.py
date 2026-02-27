"""MGB Dash 2026 — Alert evaluator for display contexts."""

import time
from dataclasses import dataclass
from typing import List

from rendering.colors import ALERT_RED, ALERT_YELLOW, ALERT_CYAN
from rendering.fonts import select_sans
from rendering.cairo_helpers import draw_text_centered

# Severity icons (Unicode symbols)
ICON_RED    = "\u2716"   # heavy X
ICON_YELLOW = "\u26a0"   # warning triangle
ICON_CYAN   = "\u2139"   # info circle


@dataclass
class Alert:
    """A single active alert."""
    message: str
    color: tuple          # RGBA
    icon: str             # Unicode severity icon
    first_seen: float     # monotonic timestamp

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.first_seen


# (check_fn, message, color, icon) — check_fn receives signals dict + heartbeats dict
_ALERT_DEFS = [
    (
        lambda s, h: any(
            hb.age_seconds > 10
            for hb in h.values()
        ),
        "HEARTBEAT LOST",
        ALERT_YELLOW,
        ICON_YELLOW,
    ),
    (
        lambda s, h: (
            "battery_temp_c" in s and
            s["battery_temp_c"].value > 45
        ),
        "BATT TEMP HIGH",
        ALERT_RED,
        ICON_RED,
    ),
    (
        lambda s, h: (
            "motor_temp_c" in s and
            s["motor_temp_c"].value > 120
        ),
        "MOTOR TEMP HIGH",
        ALERT_RED,
        ICON_RED,
    ),
    (
        lambda s, h: (
            "gps_latitude" not in s or
            s["gps_latitude"].age_seconds > 30
        ),
        "NO GPS FIX",
        ALERT_CYAN,
        ICON_CYAN,
    ),
]

# Dim alpha multiplier for alerts older than 10s
_FADE_AGE = 10.0


class AlertEvaluator:
    """Checks VehicleState for alert conditions.

    Usage:
        evaluator = AlertEvaluator()
        alerts = evaluator.get_active_alerts(state)
    """

    def __init__(self):
        self._first_seen: dict[str, float] = {}

    def get_active_alerts(self, state) -> List[Alert]:
        """Return list of currently active alerts."""
        signals = state.get_all_signals()
        heartbeats = state.get_heartbeats()
        now = time.monotonic()

        active = []
        seen_keys = set()

        for check_fn, message, color, icon in _ALERT_DEFS:
            try:
                if check_fn(signals, heartbeats):
                    seen_keys.add(message)
                    if message not in self._first_seen:
                        self._first_seen[message] = now
                    alert = Alert(
                        message=message,
                        color=color,
                        icon=icon,
                        first_seen=self._first_seen[message],
                    )
                    # Fade after _FADE_AGE
                    if alert.age_seconds > _FADE_AGE:
                        r, g, b, _ = color
                        alert.color = (r, g, b, 0.35)
                    active.append(alert)
            except Exception:
                pass  # skip broken checks

        # Clear first_seen for alerts that are no longer active
        for key in list(self._first_seen):
            if key not in seen_keys:
                del self._first_seen[key]

        return active


def draw_alert(ctx, alert: Alert, cx: float, cy: float):
    """Draw an alert with severity icon + colored text."""
    text = f"{alert.icon}  {alert.message}"
    select_sans(ctx, 16, bold=True)
    ctx.set_source_rgba(*alert.color)
    draw_text_centered(ctx, text, cx, cy)
