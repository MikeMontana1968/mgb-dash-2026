#!/usr/bin/env python3
"""
python/tools/codegen.py — Generate Python modules from common/can_ids.json

Reads the single source of truth and regenerates:
  common/python/can_ids.py
  common/python/leaf_messages.py
  common/python/resolve_messages.py

Usage:  python python/tools/codegen.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
JSON_PATH = ROOT / "common" / "can_ids.json"
PY_DIR = ROOT / "common" / "python"


# ── Helpers ──────────────────────────────────────────────────────────────

def load():
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def camel_to_snake(name):
    """CamelCase / PascalCase → snake_case."""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return s.lower()


def parse_enum_string(text):
    """Parse '0=DAYLIGHT, 1=EARLY_TWILIGHT, ...' → [(0, 'DAYLIGHT'), ...]"""
    return [(int(m.group(1), 0), m.group(2))
            for m in re.finditer(r'(0x[\dA-Fa-f]+|\d+)=(\w+)', text)]


def fmt_factor_offset(raw_var, factor, offset, has_factor, has_offset):
    """Build 'raw * factor ± offset' expression string."""
    if has_factor and has_offset:
        op = f"+ {offset}" if offset >= 0 else f"- {abs(offset)}"
        return f"{raw_var} * {factor} {op}"
    if has_factor:
        return f"{raw_var} * {factor}"
    # has_offset only
    if offset >= 0:
        return f"{raw_var} + {offset}"
    return f"{raw_var} - {abs(offset)}"


# ── Signal decode code generation ────────────────────────────────────────

def gen_signal_body(signals):
    """Generate extraction code for a message's signals.

    Returns (setup_lines, return_entries):
      setup_lines   — list of '    var = expr' strings (4-space indent)
      return_entries — list of (key, expr_str) for the return dict
    """
    setup = []
    entries = []

    for sig_name, sig in signals.items():
        key = sig.get("py_key", camel_to_snake(sig_name))
        sb = sig["start_byte"]
        sbit = sig.get("start_bit", 0)
        bits = sig["length_bits"]
        signed = sig.get("signed", False)
        factor = sig.get("factor")
        offset = sig.get("offset")
        has_factor = factor is not None and factor != 1
        has_offset = offset is not None and offset != 0

        # ── 1-bit boolean ─────────────────────────────────────────────
        if bits == 1:
            entries.append((key, f"bool(data[{sb}] & (1 << {sbit}))"))
            continue

        # ── Raw extraction expression ─────────────────────────────────
        if bits == 16 and sbit == 0:
            fmt = '">h"' if signed else '">H"'
            raw_expr = f'struct.unpack({fmt}, data[{sb}:{sb + 2}])[0]'
            sign_handled = True
        elif bits > 8:
            shift = 16 - bits - sbit
            raw_expr = f"(data[{sb}] << 8 | data[{sb + 1}]) >> {shift}"
            sign_handled = False
        elif bits == 8 and sbit == 0:
            raw_expr = f"data[{sb}]"
            sign_handled = False
        elif sbit == 0:
            mask = (1 << bits) - 1
            raw_expr = f"data[{sb}] & 0x{mask:02X}"
            sign_handled = False
        else:
            mask = (1 << bits) - 1
            raw_expr = f"(data[{sb}] >> {sbit}) & 0x{mask:02X}"
            sign_handled = False

        needs_sign = signed and not sign_handled
        needs_math = has_factor or has_offset

        # ── Simple inline (no sign ext, no factor/offset) ────────────
        if not needs_sign and not needs_math:
            entries.append((key, raw_expr))
            continue

        # ── Needs intermediate variable(s) ───────────────────────────
        raw_var = f"{key}_raw" if needs_math else key
        setup.append(f"    {raw_var} = {raw_expr}")

        if needs_sign:
            if bits == 8:
                setup.append(f"    if {raw_var} > 127:")
                setup.append(f"        {raw_var} -= 256")
            else:
                sign_bit = 1 << (bits - 1)
                full_range = 1 << bits
                setup.append(f"    if {raw_var} & 0x{sign_bit:X}:")
                setup.append(f"        {raw_var} -= 0x{full_range:X}")

        if needs_math:
            expr = fmt_factor_offset(raw_var, factor, offset, has_factor, has_offset)
            setup.append(f"    {key} = {expr}")
            entries.append((key, key))
        else:
            entries.append((key, raw_var))

    return setup, entries


# ── can_ids.py ───────────────────────────────────────────────────────────

def gen_can_ids(data):
    L = []
    meta = data["meta"]
    custom = data["custom_ids"]
    leaf = data["leaf_ids"]
    resolve = data["resolve_ids"]
    roles = data["heartbeat_roles"]

    # ── Header ──
    L.extend([
        '"""',
        'MGB Dash 2026 — Custom CAN Arbitration IDs (Python)',
        '',
        'AUTO-GENERATED from common/can_ids.json — do not edit by hand.',
        'Regenerate:  python python/tools/codegen.py',
        '"""',
        '',
    ])

    # ── Custom ID range ──
    L.extend([
        '# ── Custom CAN ID range ──────────────────────────────────────────────',
        f'CAN_CUSTOM_ID_MIN = {meta["custom_id_range"]["min"]}',
        f'CAN_CUSTOM_ID_MAX = {meta["custom_id_range"]["max"]}',
        '',
    ])

    # ── Heartbeat ──
    hb = custom["0x700"]
    rate = hb.get("rate_hz", 1)
    L.extend([
        '# ── Heartbeat (all modules) ─────────────────────────────────────────',
        'CAN_ID_HEARTBEAT = 0x700',
        'HEARTBEAT_LEN = 8',
        f'HEARTBEAT_INTERVAL_S = {1.0 / rate}',
        '',
    ])

    # Role names
    L.append('# Heartbeat role names — 5 bytes, space-padded')
    max_var = max(len(f'ROLE_{r["name"].strip()}') for r in roles)
    for r in roles:
        name = r["name"]
        var = f'ROLE_{name.strip()}'
        L.append(f'{var:<{max_var}s} = b"{name}"')
    L.append('')

    role_vars = [f'ROLE_{r["name"].strip()}' for r in roles]
    L.append(f'ALL_ROLES = [{", ".join(role_vars)}]')
    L.append('')

    # HB byte offsets (fixed structure)
    L.extend([
        '# Heartbeat payload byte offsets',
        'HB_ROLE_OFFSET = 0      # bytes 0–4: role name',
        'HB_ROLE_LEN = 5',
        'HB_UPTIME_OFFSET = 5    # byte 5: rolling counter 0–255',
        'HB_ERROR_OFFSET = 6     # byte 6: error flags bitfield',
        'HB_RESERVED_OFFSET = 7  # byte 7: reserved (0x00)',
        '',
    ])

    # ── Body Controller ──
    L.append('# ── Body Controller ─────────────────────────────────────────────────')
    body_keys = sorted(k for k in custom if custom[k]["name"].startswith("BODY_"))
    if body_keys:
        max_name = max(len(custom[k]["name"]) for k in body_keys)
        for hex_str in body_keys:
            msg = custom[hex_str]
            rate_hz = msg.get("rate_hz", "")
            rate_str = f", {rate_hz} Hz" if isinstance(rate_hz, (int, float)) else ""
            L.append(f'CAN_ID_{msg["name"]:<{max_name}s} = {hex_str}  # {msg["description"]}{rate_str}')
    L.append('')

    # Body state flags
    body_state = custom.get("0x710", {})
    byte0 = body_state.get("payload", {}).get("byte_0", {})
    if isinstance(byte0, dict):
        flags = [(int(m.group(1)), name)
                 for key, name in byte0.items()
                 for m in [re.match(r'bit_(\d+)', key)] if m]
        flags.sort()
        if flags:
            L.append('# Body state bit flags (byte 0 of 0x710 payload)')
            max_fl = max(len(name) for _, name in flags)
            for bit, name in flags:
                L.append(f'BODY_FLAG_{name:<{max_fl}s} = 1 << {bit}')
            L.append('')

    # Gear values
    gear_desc = custom.get("0x712", {}).get("payload", {}).get("byte_0", "")
    if isinstance(gear_desc, str) and gear_desc:
        enums = parse_enum_string(gear_desc)
        range_m = re.search(r'\((\d+)[–\-](\d+)\)', gear_desc)
        if enums or range_m:
            L.append('# Gear values (byte 0 of 0x712 payload)')
            for val, name in enums:
                if val > 9:
                    L.append(f'GEAR_{name.upper()} = 0x{val:02X}')
                else:
                    L.append(f'GEAR_{name.upper()} = {val}')
            if range_m:
                lo, hi = int(range_m.group(1)), int(range_m.group(2))
                existing = {v for v, _ in enums}
                for g in range(lo, hi + 1):
                    if g not in existing:
                        L.append(f'GEAR_{g} = {g}')
            L.append('')

    # ── Self-Test ──
    L.extend([
        '# ── Self-Test Command ──────────────────────────────────────────────',
        f'CAN_ID_SELF_TEST      = 0x730  # {custom.get("0x730", {}).get("description", "")}',
        'SELF_TEST_TARGET_ALL  = 0xFF   # byte 0 = 0xFF \u2192 all modules',
        '',
    ])

    # ── Logging ──
    L.extend([
        '# ── Logging \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500',
        f'CAN_ID_LOG              = 0x731  # {custom.get("0x731", {}).get("description", "")}',
        f'CAN_ID_LOG_TEXT         = 0x732  # {custom.get("0x732", {}).get("description", "")}',
        'LOG_DLC                 = 8      # LOG frame is always 8 bytes',
        'LOG_TEXT_DLC            = 8      # LOG_TEXT frame is always 8 bytes',
        'LOG_TEXT_MAX_FRAMES     = 7      # Max text continuation frames',
        'LOG_TEXT_CHARS_PER_FRAME = 7     # 7 ASCII chars per text frame',
        '',
    ])

    # ── GPS Module ──
    L.append('# \u2500\u2500 GPS Module \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')
    gps_keys = sorted(k for k in custom if custom[k]["name"].startswith("GPS_"))
    if gps_keys:
        max_name = max(len(custom[k]["name"]) for k in gps_keys)
        for hex_str in gps_keys:
            msg = custom[hex_str]
            L.append(f'CAN_ID_{msg["name"]:<{max_name}s} = {hex_str}  # {msg["description"]}')
    L.append('')

    # Ambient light categories
    ambient_desc = custom.get("0x726", {}).get("payload", {}).get("byte_0", "")
    if isinstance(ambient_desc, str):
        enums = parse_enum_string(ambient_desc)
        if enums:
            L.append('# Ambient light categories')
            max_name = max(len(name) for _, name in enums)
            for val, name in enums:
                L.append(f'AMBIENT_{name:<{max_name}s} = {val}')
            L.append('')
            L.append('AMBIENT_NAMES = {')
            for val, name in enums:
                L.append(f'    AMBIENT_{name}: "{name}",')
            L.append('}')
            L.append('')

    # ── Resolve EV Controller ──
    L.append('# \u2500\u2500 Resolve EV Controller \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')
    for hex_str, msg in sorted(resolve.items()):
        L.append(f'CAN_ID_{msg["name"]} = {hex_str}')
    L.append('')

    # ── Leaf EV-CAN IDs ──
    L.append('# \u2500\u2500 Leaf EV-CAN IDs (AZE0, 2013\u20132017) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')
    leaf_items = sorted(leaf.items(), key=lambda x: int(x[0], 16))
    if leaf_items:
        max_name = max(len(msg["name"]) for _, msg in leaf_items)
        for hex_str, msg in leaf_items:
            L.append(f'CAN_ID_{msg["name"]:<{max_name}s} = {hex_str}')
    L.append('')

    # ── CAN bus configuration ──
    speed = meta["bus_speed_kbps"]
    L.extend([
        '# \u2500\u2500 CAN bus configuration \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500',
        f'CAN_BUS_SPEED = {speed * 1000}  # {speed} kbps',
    ])

    return '\n'.join(L) + '\n'


# ── leaf_messages.py ─────────────────────────────────────────────────────

def gen_leaf_messages(data):
    L = []
    leaf = data["leaf_ids"]

    needs_struct = any(
        sig.get("length_bits", 0) == 16 and sig.get("start_bit", 0) == 0
        for msg in leaf.values()
        for sig in msg.get("signals", {}).values()
    )

    L.extend([
        '"""',
        'MGB Dash 2026 — Leaf AZE0 CAN Message Decode Constants (Python)',
        '',
        'AUTO-GENERATED from common/can_ids.json — do not edit by hand.',
        'Regenerate:  python python/tools/codegen.py',
        '',
        'All byte offsets are 0-indexed. Multi-byte values are big-endian',
        'unless noted otherwise.',
        '"""',
        '',
    ])

    if needs_struct:
        L.extend(['import struct', '', ''])

    decoders = []

    for hex_str, msg in sorted(leaf.items(), key=lambda x: int(x[0], 16)):
        id_short = hex_str[2:]   # "1DA"
        id_lower = id_short.lower()

        L.append(f'# {"=" * 69}')
        L.append(f'# {hex_str} \u2014 {msg["description"]}')
        L.append(f'# {"=" * 69}')
        L.append(f'LEAF_{id_short}_ID = {hex_str}')

        signals = msg.get("signals", {})
        if not signals:
            L.append(f'# No payload decode — presence on bus confirms this message')
            L.append('')
            L.append('')
            continue

        func_name = f'decode_{id_lower}'
        L.append('')
        L.append(f'def {func_name}(data: bytes) -> dict:')
        L.append(f'    """Decode {hex_str} \u2014 {msg["description"]}."""')

        setup, entries = gen_signal_body(signals)
        for line in setup:
            L.append(line)

        L.append('    return {')
        for key, expr in entries:
            L.append(f'        "{key}": {expr},')
        L.append('    }')
        L.append('')
        L.append('')

        decoders.append((f'LEAF_{id_short}_ID', func_name))

    # Decoder dispatch table
    L.append(f'# {"=" * 69}')
    L.append('# Decoder dispatch table')
    L.append(f'# {"=" * 69}')
    L.append('DECODERS = {')
    for id_const, func_name in decoders:
        L.append(f'    {id_const}: {func_name},')
    L.append('}')

    return '\n'.join(L) + '\n'


# ── resolve_messages.py ──────────────────────────────────────────────────

def gen_resolve_messages(data):
    L = []
    resolve = data["resolve_ids"]

    needs_struct = any(
        sig.get("length_bits", 0) == 16 and sig.get("start_bit", 0) == 0
        for msg in resolve.values()
        for sig in msg.get("signals", {}).values()
    )

    L.extend([
        '"""',
        'MGB Dash 2026 — Resolve EV Controller CAN Message Decode Constants (Python)',
        '',
        'AUTO-GENERATED from common/can_ids.json — do not edit by hand.',
        'Regenerate:  python python/tools/codegen.py',
        '"""',
        '',
    ])

    if needs_struct:
        L.extend(['import struct', ''])

    for hex_str, msg in sorted(resolve.items()):
        id_short = hex_str[2:]
        id_lower = id_short.lower()

        L.append(f'RESOLVE_{id_short}_ID = {hex_str}')

        signals = msg.get("signals", {})
        if not signals:
            continue

        L.append('')
        L.append('')
        L.append(f'def decode_{id_lower}(data: bytes) -> dict:')
        L.append(f'    """Decode {hex_str} \u2014 {msg["description"]}."""')

        setup, entries = gen_signal_body(signals)
        for line in setup:
            L.append(line)

        L.append('    return {')
        for key, expr in entries:
            L.append(f'        "{key}": {expr},')
        L.append('    }')

    return '\n'.join(L) + '\n'


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print(f"codegen: reading {JSON_PATH.relative_to(ROOT)}")
    data = load()

    targets = [
        (PY_DIR / "can_ids.py",          gen_can_ids(data)),
        (PY_DIR / "leaf_messages.py",     gen_leaf_messages(data)),
        (PY_DIR / "resolve_messages.py",  gen_resolve_messages(data)),
    ]

    for path, content in targets:
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"  wrote {path.relative_to(ROOT)}")

    print("Done.")


if __name__ == "__main__":
    main()
