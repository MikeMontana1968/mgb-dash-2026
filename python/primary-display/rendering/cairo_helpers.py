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


def _draw_end_cap(ctx: cairo.Context, cx: float, cy: float,
                  inner_r: float, outer_r: float,
                  angle: float, color: tuple):
    """Draw a rounded end cap (filled circle) at the given angle."""
    mid_r = (inner_r + outer_r) / 2
    cap_r = (outer_r - inner_r) / 2
    cap_x = cx + mid_r * math.cos(angle)
    cap_y = cy + mid_r * math.sin(angle)
    ctx.set_source_rgba(*color)
    ctx.new_path()
    ctx.arc(cap_x, cap_y, cap_r, 0, 2 * math.pi)
    ctx.fill()


def draw_arc_gauge(ctx: cairo.Context, cx: float, cy: float,
                   inner_r: float, outer_r: float,
                   start_angle: float, sweep: float,
                   fill_ratio: float, color: tuple,
                   track_color: tuple):
    """Draw an annular arc gauge: dark track (full sweep) + colored fill.

    Angles are in radians (Cairo convention: 0 = east, positive = clockwise).
    fill_ratio is clamped to 0.0–1.0.  End (right side) is rounded.
    """
    fill_ratio = max(0.0, min(1.0, fill_ratio))
    end_angle = start_angle + sweep

    # Background track (full sweep) + rounded end cap
    ctx.set_source_rgba(*track_color)
    ctx.new_path()
    ctx.arc(cx, cy, outer_r, start_angle, end_angle)
    ctx.arc_negative(cx, cy, inner_r, end_angle, start_angle)
    ctx.close_path()
    ctx.fill()
    _draw_end_cap(ctx, cx, cy, inner_r, outer_r, end_angle, track_color)

    # Colored fill + rounded end cap
    if fill_ratio > 0.001:
        fill_sweep = sweep * fill_ratio
        fill_end = start_angle + fill_sweep
        ctx.set_source_rgba(*color)
        ctx.new_path()
        ctx.arc(cx, cy, outer_r, start_angle, fill_end)
        ctx.arc_negative(cx, cy, inner_r, fill_end, start_angle)
        ctx.close_path()
        ctx.fill()
        _draw_end_cap(ctx, cx, cy, inner_r, outer_r, fill_end, color)


def draw_arc_fill(ctx: cairo.Context, cx: float, cy: float,
                  inner_r: float, outer_r: float,
                  start_angle: float, sweep: float,
                  color: tuple, round_end: bool = True):
    """Draw a single colored annular wedge (no background track).
    End (right side) is rounded by default.
    """
    if sweep < 0.001:
        return
    end_angle = start_angle + sweep
    ctx.set_source_rgba(*color)
    ctx.new_path()
    ctx.arc(cx, cy, outer_r, start_angle, end_angle)
    ctx.arc_negative(cx, cy, inner_r, end_angle, start_angle)
    ctx.close_path()
    ctx.fill()
    if round_end:
        _draw_end_cap(ctx, cx, cy, inner_r, outer_r, end_angle, color)


def chord_half_width(y: float, center: float, radius: float) -> float:
    """Return half the chord width at vertical position y in the circle."""
    dy = abs(y - center)
    if dy >= radius:
        return 0.0
    return math.sqrt(radius * radius - dy * dy)
