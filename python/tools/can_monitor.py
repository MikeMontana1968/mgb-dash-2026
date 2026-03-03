#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Monitor

Real-time decoded CAN traffic viewer with freshness color coding
and filtering by module/source. Full-screen ANSI terminal display.

Usage: python can_monitor.py [--filter BODY,GPS,LEAF] [--interface can0]
"""

import sys
import os
import struct
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import can

from common.python import can_ids
from common.python import leaf_messages
from common.python import resolve_messages
from common.python.log_setup import setup_logging

logger = setup_logging("can-monitor")

# ── ID-to-name mapping ──────────────────────────────────────────────────────

ID_NAMES = {
    0x700: "HEARTBEAT",
    0x710: "BODY_STATE",
    0x711: "BODY_SPEED",
    0x712: "BODY_GEAR",
    0x713: "BODY_ODO",
    0x720: "GPS_SPEED",
    0x721: "GPS_TIME",
    0x722: "GPS_DATE",
    0x723: "GPS_LAT",
    0x724: "GPS_LON",
    0x725: "GPS_ELEV",
    0x726: "GPS_AMBIENT",
    0x727: "GPS_UTCOFF",
    0x730: "SELF_TEST",
    0x731: "LOG",
    0x732: "LOG_TEXT",
}

# Add Leaf IDs
for arb_id, info in __import__("json").load(
    open(os.path.join(os.path.dirname(__file__), "..", "..", "common", "can_ids.json"))
).get("leaf_ids", {}).items():
    ID_NAMES[int(arb_id, 16)] = info["name"]

# Add Resolve IDs
ID_NAMES[0x539] = "RESOLVE_DISPLAY"

# ── Filter groups ────────────────────────────────────────────────────────────

FILTER_GROUPS = {
    "BODY": {0x710, 0x711, 0x712, 0x713},
    "GPS": {0x720, 0x721, 0x722, 0x723, 0x724, 0x725, 0x726, 0x727},
    "LEAF": set(leaf_messages.DECODERS.keys()),
    "HEARTBEAT": {0x700},
    "LOG": {0x731, 0x732},
    "RESOLVE": {0x539},
    "SELFTEST": {0x730},
}

# ── ANSI helpers ─────────────────────────────────────────────────────────────

ANSI_RESET = "\033[0m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_CLEAR = "\033[2J\033[H"

# Body state flag names (byte 0)
BODY_FLAGS_0 = [
    (can_ids.BODY_FLAG_KEY_ON,     "KEY_ON"),
    (can_ids.BODY_FLAG_BRAKE,      "BRAKE"),
    (can_ids.BODY_FLAG_REGEN,      "REGEN"),
    (can_ids.BODY_FLAG_FAN,        "FAN"),
    (can_ids.BODY_FLAG_REVERSE,    "REVERSE"),
    (can_ids.BODY_FLAG_LEFT_TURN,  "LEFT_TURN"),
    (can_ids.BODY_FLAG_RIGHT_TURN, "RIGHT_TURN"),
    (can_ids.BODY_FLAG_HAZARD,     "HAZARD"),
]

# Body state flag names (byte 1)
BODY_FLAGS_1 = [
    (can_ids.BODY_FLAG2_KEY_START,      "KEY_START"),
    (can_ids.BODY_FLAG2_KEY_ACCESSORY,  "KEY_ACC"),
    (can_ids.BODY_FLAG2_RUNNING_LIGHTS, "RUN_LIGHTS"),
    (can_ids.BODY_FLAG2_HEADLIGHTS,     "HEADLIGHTS"),
    (can_ids.BODY_FLAG2_CHARGE_PORT,    "CHARGE_PORT"),
]

GEAR_NAMES = {0: "N", 1: "1", 2: "2", 3: "3", 4: "4", 0xFF: "?"}

SELF_TEST_TARGETS = {
    0xFF: "ALL", 0x46: "FUEL", 0x41: "AMPS", 0x54: "TEMP",
    0x53: "SPEED", 0x42: "BODY", 0x44: "DASH", 0x47: "GPS",
}


def decode_frame(arb_id, data):
    """Decode a CAN frame into a human-readable string."""
    try:
        # Heartbeat
        if arb_id == 0x700:
            role = data[0:5].decode("ascii", errors="replace").strip()
            counter = data[5]
            err = data[6]
            return f"{role:<5s} #{counter:d} err=0x{err:02X}"

        # Body State
        if arb_id == 0x710:
            flags0 = data[0]
            flags1 = data[1]
            names = [name for mask, name in BODY_FLAGS_0 if flags0 & mask]
            names += [name for mask, name in BODY_FLAGS_1 if flags1 & mask]
            return ",".join(names) if names else "(none)"

        # Body Speed
        if arb_id == 0x711:
            speed = struct.unpack("<d", bytes(data[0:8]))[0]
            return f"{speed:.1f} mph"

        # Body Gear
        if arb_id == 0x712:
            gear = data[0]
            rev = data[1]
            gear_name = GEAR_NAMES.get(gear, f"?{gear}")
            suffix = " REV" if rev else ""
            return f"Gear={gear_name}{suffix}"

        # Body Odometer
        if arb_id == 0x713:
            miles = struct.unpack("<I", bytes(data[0:4]))[0]
            return f"{miles:,d} mi"

        # GPS Speed
        if arb_id == 0x720:
            speed = struct.unpack("<d", bytes(data[0:8]))[0]
            return f"{speed:.1f} mph"

        # GPS Time
        if arb_id == 0x721:
            secs = struct.unpack("<d", bytes(data[0:8]))[0]
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s = int(secs % 60)
            return f"{h:02d}:{m:02d}:{s:02d} UTC"

        # GPS Date
        if arb_id == 0x722:
            days = struct.unpack("<d", bytes(data[0:8]))[0]
            from datetime import datetime, timedelta
            epoch = datetime(2000, 1, 1)
            dt = epoch + timedelta(days=days)
            return dt.strftime("%Y-%m-%d")

        # GPS Lat/Lon/Elev
        if arb_id == 0x723:
            val = struct.unpack("<d", bytes(data[0:8]))[0]
            return f"{val:.6f} deg"
        if arb_id == 0x724:
            val = struct.unpack("<d", bytes(data[0:8]))[0]
            return f"{val:.6f} deg"
        if arb_id == 0x725:
            val = struct.unpack("<d", bytes(data[0:8]))[0]
            return f"{val:.1f} m"

        # GPS Ambient
        if arb_id == 0x726:
            cat = data[0]
            return can_ids.AMBIENT_NAMES.get(cat, f"?{cat}")

        # GPS UTC Offset
        if arb_id == 0x727:
            offset_min = struct.unpack("<h", bytes(data[0:2]))[0]
            sign = "+" if offset_min >= 0 else "-"
            abs_min = abs(offset_min)
            h = abs_min // 60
            m = abs_min % 60
            return f"UTC{sign}{h}:{m:02d}"

        # Self Test
        if arb_id == 0x730:
            target = data[0]
            name = SELF_TEST_TARGETS.get(target, f"0x{target:02X}")
            return f"target={name}"

        # Log
        if arb_id == 0x731:
            role_level = data[0]
            event = data[1]
            ctx = struct.unpack(">I", bytes(data[2:6]))[0]
            text_frames = data[7]
            return f"role/lvl=0x{role_level:02X} evt={event} ctx={ctx} +{text_frames}txt"

        # Log Text
        if arb_id == 0x732:
            idx = data[0]
            text = bytes(data[1:8]).decode("ascii", errors="replace").rstrip("\x00")
            return f"[{idx}] {text!r}"

        # Leaf decoders
        if arb_id in leaf_messages.DECODERS:
            decoded = leaf_messages.DECODERS[arb_id](bytes(data))
            parts = [f"{k}={v}" for k, v in decoded.items()]
            return "  ".join(parts)

        # Resolve decoders
        resolve_decoders = getattr(resolve_messages, "DECODERS", None)
        if resolve_decoders and arb_id in resolve_decoders:
            decoded = resolve_decoders[arb_id](bytes(data))
            parts = [f"{k}={v}" for k, v in decoded.items()]
            return "  ".join(parts)

    except Exception as e:
        return f"DECODE_ERR: {e}"

    # Unknown — show raw hex
    hex_str = " ".join(f"{b:02X}" for b in data)
    return f"[{len(data)}] {hex_str}"


def freshness_color(age_s):
    """Return ANSI color code based on age since last update."""
    if age_s < 1.0:
        return ANSI_GREEN
    elif age_s < 5.0:
        return ANSI_YELLOW
    else:
        return ANSI_RED


def build_filter_set(filter_str):
    """Parse comma-separated filter names into a set of CAN IDs."""
    if not filter_str:
        return None  # None = show all
    allowed = set()
    for name in filter_str.upper().split(","):
        name = name.strip()
        if name in FILTER_GROUPS:
            allowed |= FILTER_GROUPS[name]
        else:
            logger.warning("Unknown filter group: %s (known: %s)",
                           name, ", ".join(sorted(FILTER_GROUPS.keys())))
    return allowed if allowed else None


def main():
    parser = argparse.ArgumentParser(description="CAN bus monitor with decoded output")
    parser.add_argument("--interface", default="can0",
                        help="CAN interface (default: can0)")
    parser.add_argument("--filter", default="",
                        help="Comma-separated filter: BODY,GPS,LEAF,HEARTBEAT,LOG,RESOLVE,SELFTEST")
    args = parser.parse_args()

    logger.critical("CAN monitor starting on %s", args.interface)

    filter_set = build_filter_set(args.filter)
    if filter_set:
        logger.info("Filtering to IDs: %s",
                     ", ".join(f"0x{i:03X}" for i in sorted(filter_set)))

    try:
        bus = can.Bus(interface="socketcan", channel=args.interface,
                      bitrate=can_ids.CAN_BUS_SPEED)
    except Exception as e:
        logger.error("Failed to open %s: %s", args.interface, e)
        sys.exit(1)

    # State: {arb_id: (timestamp, decoded_str, raw_data)}
    state = {}
    frame_count = 0

    try:
        while True:
            msg = bus.recv(timeout=0.1)
            if msg is None:
                # No frame — still redraw for freshness updates
                pass
            else:
                arb_id = msg.arbitration_id
                if filter_set and arb_id not in filter_set:
                    continue
                decoded = decode_frame(arb_id, msg.data)
                state[arb_id] = (time.time(), decoded, msg.data)
                frame_count += 1

            # Redraw
            now = time.time()
            lines = []
            lines.append(f"{ANSI_BOLD}MGB CAN Monitor — {args.interface} — "
                         f"{frame_count} frames{ANSI_RESET}")
            lines.append(f"{ANSI_DIM}Ctrl+C to exit{ANSI_RESET}")
            lines.append("")

            for arb_id in sorted(state.keys()):
                ts, decoded, raw = state[arb_id]
                age = now - ts
                color = freshness_color(age)
                name = ID_NAMES.get(arb_id, f"0x{arb_id:03X}")
                age_str = f"{age:5.1f}s"
                lines.append(
                    f"{color}  0x{arb_id:03X}  {name:<16s}  {decoded:<50s}  {age_str}{ANSI_RESET}"
                )

            sys.stdout.write(ANSI_CLEAR + "\n".join(lines) + "\n")
            sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        bus.shutdown()
        # Clear screen and print summary
        print(f"\n{ANSI_RESET}Stopped. {frame_count} frames received.")


if __name__ == "__main__":
    main()
