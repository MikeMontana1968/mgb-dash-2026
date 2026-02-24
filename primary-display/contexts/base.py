"""MGB Dash 2026 — Context ABC for display pages."""

import abc
import cairo
from typing import Optional


class Context(abc.ABC):
    """Base class for display contexts (pages/screens).

    The cairo context arrives pre-clipped to the inscribed circle.
    """

    @abc.abstractmethod
    def render(self, ctx: cairo.Context, state, width: int, height: int):
        """Draw this context's content."""

    def on_enter(self, state):
        """Called when this context becomes active."""

    def on_exit(self):
        """Called when this context is deactivated."""

    def on_touch(self, x: int, y: int) -> Optional[str]:
        """Handle tap. Return context name to switch, or None."""
        return None

    def on_scroll(self, dy: int):
        """Handle scroll wheel (dy = notches, positive = up)."""
