"""MGB Dash 2026 — Diagnostics context: two-column CAN signal table."""

import math
from typing import Optional
from .base import Context
from rendering.colors import (
    TEXT_WHITE, TEXT_DIM, TEXT_LABEL, GROUP_HEADER, NEVER_GRAY,
    FRESH_GREEN, freshness_color,
)
from rendering.fonts import select_mono, select_sans
from rendering.cairo_helpers import chord_half_width

# (signal_key, display_label, unit, can_id_hex)
SIGNAL_GROUPS = [
    ("LEAF MOTOR", [
        ("motor_rpm",           "Motor RPM",    "RPM",  "1DA"),
        ("available_torque_nm", "Avail Torque",  "Nm",   "1DA"),
        ("failsafe",           "Failsafe",      "",     "1DA"),
    ]),
    ("LEAF BATTERY", [
        ("battery_voltage_v",   "Battery V",    "V",    "1DB"),
        ("battery_current_a",   "Battery A",    "A",    "1DB"),
        ("soc_percent",         "SOC",          "%",    "1DB"),
        ("soc_precise_percent", "SOC Precise",  "%",    "55B"),
        ("gids",                "GIDs",         "",     "5BC"),
        ("soh_percent",         "SOH",          "%",    "5BC"),
        ("battery_temp_c",      "Batt Temp",    "\u00b0F",   "5C0"),
    ]),
    ("LEAF CHARGER", [
        ("charge_power_kw", "Charge Power", "kW",  "1DC"),
    ]),
    ("LEAF TEMPS", [
        ("motor_temp_c",    "Motor Temp",    "\u00b0F",  "55A"),
        ("igbt_temp_c",     "IGBT Temp",     "\u00b0F",  "55A"),
        ("inverter_temp_c", "Inverter Temp", "\u00b0F",  "55A"),
    ]),
    ("LEAF VCM", [
        ("main_relay_closed", "Main Relay", "",  "390"),
    ]),
    ("RESOLVE", [
        ("resolve_gear",           "Gear",       "",   "539"),
        ("resolve_ignition_on",    "Ignition",   "",   "539"),
        ("resolve_system_on",      "System",     "",   "539"),
        ("resolve_regen_strength", "Regen Str",  "",   "539"),
        ("resolve_soc_percent",    "RSolve SOC", "%",  "539"),
    ]),
    ("BODY", [
        ("key_on",          "Key On",    "",    "710"),
        ("brake",           "Brake",     "",    "710"),
        ("regen",           "Regen",     "",    "710"),
        ("reverse",         "Reverse",   "",    "710"),
        ("left_turn",       "Left Turn", "",    "710"),
        ("body_speed_mph",  "Speed",     "mph", "711"),
        ("body_gear",       "Gear",      "",    "712"),
        ("odometer_miles",  "Odometer",  "mi",  "713"),
    ]),
    ("GPS", [
        ("gps_speed_mph",      "GPS Speed",  "mph", "720"),
        ("gps_latitude",       "Latitude",   "\u00b0",   "723"),
        ("gps_longitude",      "Longitude",  "\u00b0",   "724"),
        ("gps_elevation_m",    "Elevation",  "m",   "725"),
        ("gps_time_utc_s",     "Time UTC",   "s",   "721"),
        ("ambient_light_name", "Ambient",    "",    "726"),
    ]),
]

# Left: LEAF MOTOR, BATTERY, CHARGER, TEMPS, VCM  (indices 0-4)
# Right: RESOLVE, BODY, GPS                        (indices 5-7)
LEFT_GROUPS = [0, 1, 2, 3, 4]
RIGHT_GROUPS = [5, 6, 7]


class DiagnosticsContext(Context):
    ROW_H = 18
    FONT_SZ = 12
    HDR_FONT_SZ = 11
    TITLE_FONT_SZ = 18
    GRID_TOP = 70
    GRID_BOT_MARGIN = 80      # reserved at bottom for heartbeat bar
    PAD = 4                   # padding inside group borders
    COL_GAP = 8               # gap between left and right columns
    GROUP_GAP = 4             # vertical gap between group boxes

    # Character-count column spec: CAN(3) gap(1) Age(3) gap(1) Value(8) gap(1) Label(12)
    COL_CHARS = 29            # total chars per row
    CAN_CHARS = 3
    AGE_CHARS = 3
    VAL_CHARS = 8
    LBL_CHARS = 12

    def __init__(self):
        self._previous_context = "diagnostics"
        self._source_label = "synthetic"

    # ── Context interface ────────────────────────────────────────────

    def render(self, ctx, state, width, height):
        signals = state.get_all_signals()
        heartbeats = state.get_heartbeats()

        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2

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

        # ── Column geometry (character-width based, centered) ────────
        select_mono(ctx, self.FONT_SZ)
        char_w = ctx.text_extents("M").x_advance
        col_w = self.COL_CHARS * char_w + 2 * self.PAD
        total_w = 2 * col_w + self.COL_GAP
        left_x = cx - total_w / 2
        right_x = left_x + col_w + self.COL_GAP

        # ── Draw two columns ─────────────────────────────────────────
        self._draw_column(ctx, signals, LEFT_GROUPS, left_x, col_w, char_w)
        self._draw_column(ctx, signals, RIGHT_GROUPS, right_x, col_w, char_w)

        # ── Heartbeat bar ────────────────────────────────────────────
        self._draw_heartbeat_bar(ctx, heartbeats, width, height, cx, radius)

    def on_enter(self, state):
        pass  # no scroll state to reset

    def on_touch(self, x: int, y: int) -> Optional[str]:
        return self._previous_context

    def on_scroll(self, dy: int):
        pass  # no scrolling in two-column layout

    def set_previous_context(self, name: str):
        self._previous_context = name

    def set_source_label(self, label: str):
        self._source_label = label

    # ── Drawing helpers ──────────────────────────────────────────────

    def _draw_column(self, ctx, signals, group_indices, col_x, col_w, char_w):
        y = self.GRID_TOP
        for gi in group_indices:
            group_name, sigs = SIGNAL_GROUPS[gi]
            num_rows = 1 + len(sigs)  # header row + signal rows
            box_h = num_rows * self.ROW_H + 2 * self.PAD

            # Group border
            ctx.set_source_rgba(*TEXT_DIM)
            ctx.set_line_width(1)
            ctx.rectangle(col_x, y, col_w, box_h)
            ctx.stroke()

            # Group header (spans border width)
            select_mono(ctx, self.HDR_FONT_SZ, bold=True)
            ctx.set_source_rgba(*GROUP_HEADER)
            ctx.move_to(col_x + self.PAD, y + self.PAD + self.ROW_H - 4)
            ctx.show_text(group_name)

            # Signal rows
            row_y = y + self.PAD + self.ROW_H
            for sig_key, sig_label, sig_unit, can_id in sigs:
                sv = signals.get(sig_key)
                self._draw_signal_row(ctx, can_id, sig_label, sig_unit, sv,
                                      row_y, col_x, char_w)
                row_y += self.ROW_H

            y += box_h + self.GROUP_GAP

    def _draw_signal_row(self, ctx, can_id, label, unit, sv, y, col_x, char_w):
        if sv is None:
            age = float("inf")
            value_str = "---"
        else:
            age = sv.age_seconds
            value_str = self._format_value(sv.value, unit)

        color = freshness_color(age)
        # Age display: green checkmark if < 1s, integer seconds, "---" if stale
        if age < 1.0:
            age_str = "\u2713"   # ✓
        elif age < 100:
            age_str = f"{int(age)}s"
        else:
            age_str = "---"
        text_y = y + self.ROW_H - 4
        lx = col_x + self.PAD  # inner left edge

        select_mono(ctx, self.FONT_SZ)

        # Field positions (char-count based):
        #   CAN(3) gap(1) Age(3) gap(1) Value(8) gap(1) Label(12)
        can_x = lx
        age_right = lx + 7 * char_w     # right edge of age field
        val_right = lx + 16 * char_w    # right edge of value field
        lbl_x = lx + 17 * char_w        # left edge of label field

        # CAN ID — left-aligned (3 chars)
        ctx.set_source_rgba(*TEXT_DIM)
        ctx.move_to(can_x, text_y)
        ctx.show_text(can_id[:3])

        # Age — right-aligned (3 chars), green checkmark if fresh
        if age_str == "\u2713":
            ctx.set_source_rgba(*FRESH_GREEN)
        else:
            ctx.set_source_rgba(*TEXT_DIM)
        ext = ctx.text_extents(age_str)
        ctx.move_to(age_right - ext.width, text_y)
        ctx.show_text(age_str)

        # Value — right-aligned (8 chars), freshness-colored
        value_str = value_str[:8]
        ctx.set_source_rgba(*color)
        ext = ctx.text_extents(value_str)
        ctx.move_to(val_right - ext.width, text_y)
        ctx.show_text(value_str)

        # Label — left-aligned (12 chars), white
        ctx.set_source_rgba(*TEXT_WHITE)
        ctx.move_to(lbl_x, text_y)
        ctx.show_text(label[:12])

    def _draw_heartbeat_bar(self, ctx, heartbeats, width, height, cx, radius):
        bar_y = height - 60
        roles = ["FUEL", "AMPS", "TEMP", "SPEED", "BODY", "GPS"]
        slot_w = 85
        total_w = len(roles) * slot_w
        start_x = cx - total_w / 2

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
            return "ON" if value else "OFF"
        if isinstance(value, float):
            if unit == "\u00b0F":
                value = value * 9 / 5 + 32
            return f"{value:.1f}"
        if isinstance(value, int):
            return str(value)
        return str(value)
