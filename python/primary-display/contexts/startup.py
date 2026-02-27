"""MGB Dash 2026 — Startup splash context."""

import time
from typing import Optional

from .base import Context
from rendering.colors import TEXT_WHITE, TEXT_DIM
from rendering.fonts import select_sans
from rendering.cairo_helpers import draw_text_centered

_SPLASH_DURATION = 3.0  # seconds before auto-transition to idle


class StartupContext(Context):
    """Splash screen: 'MGB DASH 2026' centered.

    Auto-transitions to idle after 3s. The ContextManager handles the
    transition via evaluate().
    """

    def __init__(self):
        self._enter_time: float | None = None

    @property
    def elapsed(self) -> float:
        """Seconds since this context was entered."""
        if self._enter_time is None:
            return 0.0
        return time.monotonic() - self._enter_time

    @property
    def ready_to_leave(self) -> bool:
        return self.elapsed >= _SPLASH_DURATION

    def render(self, ctx, state, width, height):
        cx, cy = width / 2, height / 2

        # ── Title ─────────────────────────────────────────────────────
        select_sans(ctx, 42, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        draw_text_centered(ctx, "MGB DASH", cx, cy - 20)

        select_sans(ctx, 28)
        ctx.set_source_rgba(*TEXT_DIM)
        draw_text_centered(ctx, "2026", cx, cy + 25)

    def on_enter(self, state):
        self._enter_time = time.monotonic()

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return "idle"
