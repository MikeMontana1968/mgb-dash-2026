"""MGB Dash 2026 — Font loading helpers (system fonts for Phase 1–2)."""

import sys
import cairo

_MONO = "Consolas" if sys.platform == "win32" else "monospace"
_SANS = "Segoe UI" if sys.platform == "win32" else "sans-serif"


def select_mono(ctx: cairo.Context, size: float, bold: bool = False):
    ctx.select_font_face(
        _MONO,
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)


def select_sans(ctx: cairo.Context, size: float, bold: bool = False):
    ctx.select_font_face(
        _SANS,
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
