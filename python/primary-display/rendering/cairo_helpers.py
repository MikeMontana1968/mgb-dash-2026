"""MGB Dash 2026 — Shared Cairo drawing helpers."""

import math
import cairo
from .colors import freshness_color


def clip_circle(ctx: cairo.Context, width: int, height: int):
    """Clip to the inscribed circle of the display."""
    cx, cy = width / 2, height / 2
    radius = min(width, height) / 2
    ctx.arc(cx, cy, radius, 0, 2 * math.pi)
    ctx.clip()


def fill_background(ctx: cairo.Context, color: tuple):
    ctx.set_source_rgba(*color)
    ctx.paint()


def draw_text_centered(ctx: cairo.Context, text: str, cx: float, cy: float):
    extents = ctx.text_extents(text)
    ctx.move_to(cx - extents.width / 2, cy + extents.height / 2)
    ctx.show_text(text)


def draw_freshness_bar(ctx: cairo.Context, x: float, y: float, height: float,
                       age_seconds: float):
    color = freshness_color(age_seconds)
    ctx.set_source_rgba(*color)
    ctx.rectangle(x, y, 4, height)
    ctx.fill()


def chord_half_width(y: float, center: float, radius: float) -> float:
    """Return half the chord width at vertical position y in the circle."""
    dy = abs(y - center)
    if dy >= radius:
        return 0.0
    return math.sqrt(radius * radius - dy * dy)
