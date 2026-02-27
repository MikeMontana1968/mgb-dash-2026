"""MGB Dash 2026 — CAN LOG alert manager for display contexts.

Alerts are driven by CAN LOG (0x731) and LOG_TEXT (0x732) messages.
Each alert is shown for DISPLAY_DURATION seconds then removed.
Duplicate alerts (same role+event) within the storm cooldown are
coalesced: the counter increments and the timer resets.

Usage:
    manager = AlertManager()
    manager.push(role, level, event, text)  # called from CAN decode
    alerts = manager.get_display_alerts()   # called from render loop
"""

import time
import threading
from dataclasses import dataclass, field
from typing import List

from common.python.can_log import LogLevel, LogRole, LogEvent
from rendering.colors import ALERT_RED, ALERT_YELLOW, ALERT_CYAN
from rendering.fonts import select_sans
from rendering.cairo_helpers import draw_text_centered

# Severity icons (Unicode symbols)
ICON_CRITICAL = "\u2716"   # heavy X
ICON_ERROR    = "\u2716"   # heavy X
ICON_WARN     = "\u26a0"   # warning triangle
ICON_INFO     = "\u2139"   # info circle
ICON_DEBUG    = "\u00b7"   # middle dot

# Level → (color, icon)
_LEVEL_STYLE = {
    LogLevel.LOG_CRITICAL: (ALERT_RED,    ICON_CRITICAL),
    LogLevel.LOG_ERROR:    (ALERT_RED,    ICON_ERROR),
    LogLevel.LOG_WARN:     (ALERT_YELLOW, ICON_WARN),
    LogLevel.LOG_INFO:     (ALERT_CYAN,   ICON_INFO),
    LogLevel.LOG_DEBUG:    (ALERT_CYAN,   ICON_DEBUG),
}

# Configuration
MAX_DISPLAY    = 4      # max alerts shown at once
DISPLAY_DURATION = 5.0  # seconds before auto-removal
MIN_DISPLAY_LEVEL = LogLevel.LOG_INFO  # minimum level to display (configurable)

# Storm triage: if the same (role, event) fires again within this window,
# coalesce into a single alert with an incrementing count rather than
# flooding the display.  The timer resets on each repeat so the alert
# stays visible while the storm continues, then expires normally after
# the last occurrence + DISPLAY_DURATION.
STORM_COOLDOWN = 10.0   # seconds — coalesce repeats within this window


@dataclass
class Alert:
    """A single display alert."""
    role: LogRole
    level: LogLevel
    event: LogEvent
    text: str
    color: tuple
    icon: str
    timestamp: float = field(default_factory=time.monotonic)
    count: int = 1        # storm coalesce counter

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.timestamp

    @property
    def display_text(self) -> str:
        base = self.text if self.text else self.event.name
        if self.count > 1:
            return f"{base} (x{self.count})"
        return base

    @property
    def storm_key(self) -> tuple:
        """Key for coalescing duplicate alerts."""
        return (self.role, self.event)


class AlertManager:
    """Thread-safe CAN LOG alert queue with expiry and storm triage."""

    def __init__(self, min_level: LogLevel = MIN_DISPLAY_LEVEL):
        self._lock = threading.Lock()
        self._alerts: list[Alert] = []
        self.min_level = min_level

    def push(self, role: LogRole, level: LogLevel, event: LogEvent,
             text: str = ""):
        """Add an alert from a decoded CAN LOG frame."""
        if int(level) < int(self.min_level):
            return

        color, icon = _LEVEL_STYLE.get(level, (ALERT_CYAN, ICON_INFO))
        now = time.monotonic()
        storm_key = (role, event)

        with self._lock:
            # Storm triage: coalesce if same (role, event) within cooldown
            for existing in self._alerts:
                if (existing.storm_key == storm_key
                        and (now - existing.timestamp) < STORM_COOLDOWN):
                    existing.count += 1
                    existing.timestamp = now  # reset expiry timer
                    if text:
                        existing.text = text  # update to latest text
                    return

            self._alerts.append(Alert(
                role=role,
                level=level,
                event=event,
                text=text,
                color=color,
                icon=icon,
                timestamp=now,
            ))

    def get_display_alerts(self) -> List[Alert]:
        """Return up to MAX_DISPLAY alerts, priority-sorted, expired removed."""
        now = time.monotonic()
        with self._lock:
            # Remove expired
            self._alerts = [a for a in self._alerts
                            if (now - a.timestamp) < DISPLAY_DURATION]
            # Sort by level descending (CRITICAL first), then by timestamp
            sorted_alerts = sorted(
                self._alerts,
                key=lambda a: (-int(a.level), a.timestamp),
            )
            return sorted_alerts[:MAX_DISPLAY]


def draw_alerts(ctx, alerts: List[Alert], cx: float, base_y: float,
                line_spacing: float = 20.0):
    """Draw up to MAX_DISPLAY alerts as stacked lines."""
    for i, alert in enumerate(alerts[:MAX_DISPLAY]):
        text = f"{alert.icon}  {alert.display_text}"
        y = base_y + i * line_spacing
        select_sans(ctx, 14, bold=True)
        ctx.set_source_rgba(*alert.color)
        draw_text_centered(ctx, text, cx, y)
