"""MGB Dash 2026 — Diagnostics context: CAN signal grid with freshness."""

import math
from typing import Optional
from .base import Context
from rendering.colors import (
    TEXT_WHITE, TEXT_DIM, TEXT_LABEL, GROUP_HEADER, NEVER_GRAY,
    freshness_color,
)
from rendering.fonts import select_mono, select_sans
from rendering.cairo_helpers import chord_half_width

# (signal_key, display_label, unit)
SIGNAL_GROUPS = [
    ("LEAF MOTOR", [
        ("motor_rpm",           "Motor RPM",    "RPM"),
        ("available_torque_nm", "Avail Torque",  "Nm"),
        ("failsafe",           "Failsafe",      ""),
    ]),
    ("LEAF BATTERY", [
        ("battery_voltage_v",   "Battery V",    "V"),
        ("battery_current_a",   "Battery A",    "A"),
        ("soc_percent",         "SOC",          "%"),
        ("soc_precise_percent", "SOC Precise",  "%"),
        ("gids",                "GIDs",         ""),
        ("soh_percent",         "SOH",          "%"),
        ("battery_temp_c",      "Batt Temp",    "\u00b0C"),
    ]),
    ("LEAF CHARGER", [
        ("charge_power_kw", "Charge Power", "kW"),
    ]),
    ("LEAF TEMPS", [
        ("motor_temp_c",    "Motor Temp",    "\u00b0C"),
        ("igbt_temp_c",     "IGBT Temp",     "\u00b0C"),
        ("inverter_temp_c", "Inverter Temp", "\u00b0C"),
    ]),
    ("LEAF VCM", [
        ("main_relay_closed", "Main Relay", ""),
    ]),
    ("RESOLVE", [
        ("resolve_gear",           "Gear",      ""),
        ("resolve_ignition_on",    "Ignition",  ""),
        ("resolve_system_on",      "System",    ""),
        ("resolve_regen_strength", "Regen Str", ""),
        ("resolve_soc_percent",    "RSolve SOC", "%"),
    ]),
    ("BODY", [
        ("key_on",          "Key On",    ""),
        ("brake",           "Brake",     ""),
        ("regen",           "Regen",     ""),
        ("reverse",         "Reverse",   ""),
        ("left_turn",       "Left Turn", ""),
        ("body_speed_mph",  "Speed",     "mph"),
        ("body_gear",       "Gear",      ""),
        ("odometer_miles",  "Odometer",  "mi"),
    ]),
    ("GPS", [
        ("gps_speed_mph",      "GPS Speed",  "mph"),
        ("gps_latitude",       "Latitude",   "\u00b0"),
        ("gps_longitude",      "Longitude",  "\u00b0"),
        ("gps_elevation_m",    "Elevation",  "m"),
        ("gps_time_utc_s",     "Time UTC",   "s"),
        ("ambient_light_name", "Ambient",    ""),
    ]),
]


class DiagnosticsContext(Context):
    ROW_H = 20
    FONT_SZ = 13
    HDR_FONT_SZ = 11
    TITLE_FONT_SZ = 18
    GRID_TOP = 70
    GRID_BOT_MARGIN = 80      # reserved at bottom for heartbeat bar

    def __init__(self):
        self._scroll_y = 0.0
        self._max_scroll = 0.0
        self._previous_context = "diagnostics"
        self._source_label = "synthetic"

    # ── Context interface ────────────────────────────────────────────

    def render(self, ctx, state, width, height):
        signals = state.get_all_signals()
        heartbeats = state.get_heartbeats()

        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2
        grid_bottom = height - self.GRID_BOT_MARGIN
        visible_h = grid_bottom - self.GRID_TOP

        # Count rows for scroll bounds
        total_rows = sum(1 + len(sigs) for _, sigs in SIGNAL_GROUPS)
        total_h = total_rows * self.ROW_H
        self._max_scroll = max(0.0, total_h - visible_h)
        self._scroll_y = max(0.0, min(self._scroll_y, self._max_scroll))

        # ── Title ────────────────────────────────────────────────────
        select_sans(ctx, self.TITLE_FONT_SZ, bold=True)
        ctx.set_source_rgba(*TEXT_WHITE)
        ext = ctx.text_extents("DIAGNOSTICS")
        ctx.move_to(cx - ext.width / 2, 50)
        ctx.show_text("DIAGNOSTICS")

        # Source indicator
        select_mono(ctx, 10)
        ctx.set_source_rgba(*TEXT_DIM)
        ext = ctx.text_extents(self._source_label)
        ctx.move_to(cx - ext.width / 2, 65)
        ctx.show_text(self._source_label)

        # ── Grid (clipped to visible area) ───────────────────────────
        ctx.save()
        ctx.rectangle(0, self.GRID_TOP, width, visible_h)
        ctx.clip()

        y = self.GRID_TOP - self._scroll_y
        for group_name, sigs in SIGNAL_GROUPS:
            # Group header
            if self.GRID_TOP - self.ROW_H < y < grid_bottom + self.ROW_H:
                self._draw_group_header(ctx, group_name, y, cx, radius)
            y += self.ROW_H

            for sig_key, sig_label, sig_unit in sigs:
                if self.GRID_TOP - self.ROW_H < y < grid_bottom + self.ROW_H:
                    sv = signals.get(sig_key)
                    self._draw_signal_row(ctx, sig_label, sig_unit, sv, y, cx, radius)
                y += self.ROW_H

        ctx.restore()

        # ── Heartbeat bar ────────────────────────────────────────────
        self._draw_heartbeat_bar(ctx, heartbeats, width, height, cx, radius)

    def on_enter(self, state):
        self._scroll_y = 0.0

    def on_touch(self, x: int, y: int) -> Optional[str]:
        # Tap in the title area exits diagnostics
        if y < self.GRID_TOP:
            return self._previous_context
        return None

    def on_scroll(self, dy: int):
        self._scroll_y -= dy * self.ROW_H * 3
        self._scroll_y = max(0.0, min(self._scroll_y, self._max_scroll))

    def set_previous_context(self, name: str):
        self._previous_context = name

    def set_source_label(self, label: str):
        self._source_label = label

    # ── Drawing helpers ──────────────────────────────────────────────

    def _draw_group_header(self, ctx, name, y, cx, radius):
        row_cy = y + self.ROW_H / 2
        hw = chord_half_width(row_cy, cx, radius)
        if hw < 30:
            return
        left = cx - hw + 20

        select_mono(ctx, self.HDR_FONT_SZ, bold=True)
        ctx.set_source_rgba(*GROUP_HEADER)
        ctx.move_to(left, y + self.ROW_H - 5)
        ctx.show_text(f"\u2500\u2500 {name} \u2500\u2500")

    def _draw_signal_row(self, ctx, label, unit, sv, y, cx, radius):
        row_cy = y + self.ROW_H / 2
        hw = chord_half_width(row_cy, cx, radius)
        if hw < 40:
            return
        left = cx - hw + 12
        right = cx + hw - 12

        if sv is None:
            age = float("inf")
            value_str = "---"
        else:
            age = sv.age_seconds
            value_str = self._format_value(sv.value, unit)

        color = freshness_color(age)

        # Freshness bar
        ctx.set_source_rgba(*color)
        ctx.rectangle(left, y + 2, 4, self.ROW_H - 4)
        ctx.fill()

        # Label
        select_mono(ctx, self.FONT_SZ)
        ctx.set_source_rgba(*TEXT_LABEL)
        ctx.move_to(left + 12, y + self.ROW_H - 5)
        ctx.show_text(label)

        # Value
        ctx.set_source_rgba(*color)
        ctx.move_to(left + 170, y + self.ROW_H - 5)
        ctx.show_text(value_str)

        # Age
        age_str = f"{age:.1f}s" if age < 999 else "never"
        ctx.set_source_rgba(*TEXT_DIM)
        # Right-align age
        select_mono(ctx, 11)
        ext = ctx.text_extents(age_str)
        ctx.move_to(right - ext.width, y + self.ROW_H - 5)
        ctx.show_text(age_str)

    def _draw_heartbeat_bar(self, ctx, heartbeats, width, height, cx, radius):
        bar_y = height - 60
        roles = ["FUEL", "AMPS", "TEMP", "SPEED", "BODY", "GPS"]
        slot_w = 85
        total_w = len(roles) * slot_w
        start_x = cx - total_w / 2

        # Background band
        select_mono(ctx, 10, bold=True)
        for i, role in enumerate(roles):
            x = start_x + i * slot_w
            hb = heartbeats.get(role)
            color = freshness_color(hb.age_seconds) if hb else NEVER_GRAY

            # Dot
            ctx.set_source_rgba(*color)
            ctx.arc(x + 8, bar_y + 6, 4, 0, 2 * math.pi)
            ctx.fill()

            # Label
            ctx.set_source_rgba(*TEXT_DIM)
            ctx.move_to(x + 16, bar_y + 10)
            ctx.show_text(role)

    @staticmethod
    def _format_value(value, unit: str) -> str:
        if isinstance(value, bool):
            text = "ON" if value else "OFF"
        elif isinstance(value, float):
            text = f"{value:.1f}"
        elif isinstance(value, int):
            text = str(value)
        else:
            text = str(value)
        if unit:
            text += f" {unit}"
        return text
