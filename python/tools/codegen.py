#!/usr/bin/env python3
"""
python/tools/codegen.py — Generate Python + C++ modules from common/can_ids.json

Reads the single source of truth and regenerates:
  common/python/can_ids.py
  common/python/leaf_messages.py
  common/python/resolve_messages.py
  common/cpp/can_ids.h
  common/cpp/leaf_messages.h
  common/cpp/resolve_messages.h

Usage:  python python/tools/codegen.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
JSON_PATH = ROOT / "common" / "can_ids.json"
PY_DIR = ROOT / "common" / "python"
CPP_DIR = ROOT / "common" / "cpp"


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

    # Body state flags — byte 0
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

    # Body state flags — byte 1
    byte1 = body_state.get("payload", {}).get("byte_1", {})
    if isinstance(byte1, dict):
        flags1 = [(int(m.group(1)), name)
                  for key, name in byte1.items()
                  for m in [re.match(r'bit_(\d+)', key)] if m]
        flags1.sort()
        if flags1:
            L.append('# Body state bit flags (byte 1 of 0x710 payload)')
            max_fl = max(len(name) for _, name in flags1)
            for bit, name in flags1:
                L.append(f'BODY_FLAG2_{name:<{max_fl}s} = 1 << {bit}')
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


# ── C++ signal helpers ───────────────────────────────────────────────────

def cpp_signal_block(sig_name, sig):
    """Generate C++ constexpr lines for one signal. Returns list of strings."""
    key = sig.get("cpp_key", sig_name.upper())
    sb = sig["start_byte"]
    sbit = sig.get("start_bit", 0)
    bits = sig["length_bits"]
    factor = sig.get("factor")
    offset = sig.get("offset")
    has_factor = factor is not None and factor != 1
    has_offset = offset is not None and offset != 0

    lines = []

    if bits == 1:
        # Single bit
        lines.append(f"    constexpr uint8_t {key}_BYTE = {sb};")
        lines.append(f"    constexpr uint8_t {key}_BIT  = {sbit};")
    elif bits > 8:
        # Multi-byte
        lines.append(f"    constexpr uint8_t {key}_BYTE_HI = {sb};")
        lines.append(f"    constexpr uint8_t {key}_BYTE_LO = {sb + 1};")
        if bits < 16:
            lines.append(f"    constexpr uint8_t {key}_BITS    = {bits};")
    elif bits == 8 and sbit == 0:
        # Full byte
        lines.append(f"    constexpr uint8_t {key}_BYTE = {sb};")
    else:
        # Sub-byte (>1 bit, <=8 bits)
        mask = (1 << bits) - 1
        lines.append(f"    constexpr uint8_t {key}_BYTE  = {sb};")
        if sbit > 0:
            lines.append(f"    constexpr uint8_t {key}_SHIFT = {sbit};")
        lines.append(f"    constexpr uint8_t {key}_MASK  = 0x{mask:02X};")

    if has_factor:
        lines.append(f"    constexpr float   {key}_FACTOR  = {factor}f;")
    if has_offset:
        if isinstance(offset, float) or (has_factor and isinstance(factor, float)):
            lines.append(f"    constexpr float   {key}_OFFSET  = {float(offset)}f;")
        else:
            lines.append(f"    constexpr int8_t  {key}_OFFSET = {offset};")

    return lines


def gen_messages_h(messages, namespace_prefix, header_title, header_extra=""):
    """Generate a C++ header for a set of CAN messages (Leaf or Resolve)."""
    L = [
        "#pragma once",
        "/**",
        f" * MGB Dash 2026 \u2014 {header_title}",
        " *",
        " * AUTO-GENERATED from common/can_ids.json \u2014 do not edit by hand.",
        " * Regenerate:  python python/tools/codegen.py",
        " *",
        " * All byte offsets are 0-indexed. Multi-byte values are big-endian",
        " * unless noted otherwise.",
        " */",
        "",
        "#include <cstdint>",
    ]
    if header_extra:
        L.append(header_extra)

    for hex_str, msg in sorted(messages.items(), key=lambda x: int(x[0], 16)):
        id_short = hex_str[2:]  # "1DA"
        name = msg["name"]
        desc = msg.get("description", "")
        signals = msg.get("signals", {})

        L.append("")
        L.append(f"// {'=' * 67}")
        L.append(f"// {hex_str} \u2014 {desc} ({name})")
        L.append(f"// {'=' * 67}")
        L.append(f"namespace {namespace_prefix}{id_short} {{")
        L.append(f"    constexpr uint32_t ID = {hex_str};")

        if signals:
            L.append(f"    constexpr uint8_t  DLC = 8;")

            for sig_name, sig in signals.items():
                L.append("")
                # Comment describing the signal
                key = sig.get("cpp_key", sig_name.upper())
                sb = sig["start_byte"]
                bits = sig["length_bits"]
                sbit = sig.get("start_bit", 0)
                if bits == 1:
                    L.append(f"    // {sig_name} \u2014 byte {sb}, bit {sbit}")
                elif bits > 8:
                    L.append(f"    // {sig_name} \u2014 bytes {sb}\u2013{sb+1}, {'upper ' if bits < 16 else ''}{bits} bits, big-endian")
                elif sbit > 0:
                    L.append(f"    // {sig_name} \u2014 byte {sb}, bits {sbit}\u2013{sbit + bits - 1}")
                else:
                    L.append(f"    // {sig_name} \u2014 byte {sb}")

                for line in cpp_signal_block(sig_name, sig):
                    L.append(line)
        else:
            L.append(f"    // Presence of this ID on the bus confirms {desc}")
            L.append(f"    // No specific payload decode needed \u2014 just check for presence")

        L.append("}")

    return "\n".join(L) + "\n"


# ── can_ids.h ────────────────────────────────────────────────────────────

def gen_can_ids_h(data):
    L = []
    meta = data["meta"]
    custom = data["custom_ids"]
    leaf = data["leaf_ids"]
    resolve = data["resolve_ids"]
    roles = data["heartbeat_roles"]

    # Header
    L.extend([
        "#pragma once",
        "/**",
        " * MGB Dash 2026 \u2014 Custom CAN Arbitration IDs",
        " *",
        " * AUTO-GENERATED from common/can_ids.json \u2014 do not edit by hand.",
        " * Regenerate:  python python/tools/codegen.py",
        " */",
        "",
        "#include <cstdint>",
        "",
    ])

    # Custom ID range
    L.extend([
        "// \u2500\u2500 Custom CAN ID range \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        f'constexpr uint32_t CAN_CUSTOM_ID_MIN = {meta["custom_id_range"]["min"]};',
        f'constexpr uint32_t CAN_CUSTOM_ID_MAX = {meta["custom_id_range"]["max"]};',
        "",
    ])

    # Heartbeat
    hb = custom["0x700"]
    rate = hb.get("rate_hz", 1)
    interval_ms = int(1000 / rate)
    L.extend([
        "// \u2500\u2500 Heartbeat (all modules) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        "constexpr uint32_t CAN_ID_HEARTBEAT = 0x700;",
        "constexpr uint8_t  HEARTBEAT_LEN    = 8;",
        f"constexpr uint16_t HEARTBEAT_INTERVAL_MS = {interval_ms};",
        "",
    ])

    # Role names
    L.append("// Heartbeat role names \u2014 5 bytes, space-padded")
    max_var = max(len(f"ROLE_{r['name'].strip()}") for r in roles)
    for r in roles:
        name = r["name"]
        var = f'ROLE_{name.strip()}'
        # constexpr char ROLE_FUEL[6] = "FUEL ";
        L.append(f'constexpr char {var + "[6]":<{max_var + 3}s} = "{name}";')
    L.append("")

    # HB byte offsets
    L.extend([
        "// Heartbeat payload byte offsets",
        "constexpr uint8_t HB_ROLE_OFFSET    = 0;  // bytes 0\u20134: role name",
        "constexpr uint8_t HB_ROLE_LEN       = 5;",
        "constexpr uint8_t HB_UPTIME_OFFSET  = 5;  // byte 5: rolling counter 0\u2013255",
        "constexpr uint8_t HB_ERROR_OFFSET   = 6;  // byte 6: error flags bitfield",
        "constexpr uint8_t HB_RESERVED_OFFSET = 7; // byte 7: reserved (0x00)",
        "",
    ])

    # Body Controller IDs
    L.append("// \u2500\u2500 Body Controller \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    body_keys = sorted(k for k in custom if custom[k]["name"].startswith("BODY_"))
    if body_keys:
        max_name = max(len(f'CAN_ID_{custom[k]["name"]}') for k in body_keys)
        for hex_str in body_keys:
            msg = custom[hex_str]
            rate_hz = msg.get("rate_hz", "")
            rate_str = f", {rate_hz} Hz" if isinstance(rate_hz, (int, float)) else ""
            L.append(f'constexpr uint32_t {"CAN_ID_" + msg["name"]:<{max_name + 4}s} = {hex_str};  // {msg["description"]}{rate_str}')
    L.append("")

    # Body state flags — byte 0
    body_state = custom.get("0x710", {})
    byte0 = body_state.get("payload", {}).get("byte_0", {})
    if isinstance(byte0, dict):
        flags = [(int(m.group(1)), name)
                 for key, name in byte0.items()
                 for m in [re.match(r'bit_(\d+)', key)] if m]
        flags.sort()
        if flags:
            L.append("// Body state bit flags \u2014 byte 0 of 0x710 payload")
            max_fl = max(len(f"BODY_FLAG_{name}") for _, name in flags)
            for bit, name in flags:
                L.append(f'constexpr uint8_t {"BODY_FLAG_" + name:<{max_fl + 2}s} = (1 << {bit});')
            L.append("")

    # Body state flags — byte 1
    byte1 = body_state.get("payload", {}).get("byte_1", {})
    if isinstance(byte1, dict):
        flags1 = [(int(m.group(1)), name)
                  for key, name in byte1.items()
                  for m in [re.match(r'bit_(\d+)', key)] if m]
        flags1.sort()
        if flags1:
            L.append("// Body state bit flags \u2014 byte 1 of 0x710 payload")
            max_fl = max(len(f"BODY_FLAG2_{name}") for _, name in flags1)
            for bit, name in flags1:
                L.append(f'constexpr uint8_t {"BODY_FLAG2_" + name:<{max_fl + 2}s} = (1 << {bit});')
            L.append("")

    # Gear values (hardcoded protocol constants)
    L.extend([
        "// Gear values (byte 0 of 0x712 payload)",
        "constexpr uint8_t GEAR_NEUTRAL = 0;",
        "constexpr uint8_t GEAR_1       = 1;",
        "constexpr uint8_t GEAR_2       = 2;",
        "constexpr uint8_t GEAR_3       = 3;",
        "constexpr uint8_t GEAR_4       = 4;",
        "constexpr uint8_t GEAR_UNKNOWN = 0xFF;",
        "",
    ])

    # Self-Test
    L.extend([
        "// \u2500\u2500 Self-Test Command \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        "constexpr uint32_t CAN_ID_SELF_TEST      = 0x730;  // On-demand self-test trigger",
        "constexpr uint8_t  SELF_TEST_TARGET_ALL  = 0xFF;   // byte 0 = 0xFF \u2192 all modules",
        "",
    ])

    # Logging
    L.extend([
        "// \u2500\u2500 Logging \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        "constexpr uint32_t CAN_ID_LOG            = 0x731;  // Structured log event",
        "constexpr uint32_t CAN_ID_LOG_TEXT       = 0x732;  // Log text continuation (up to 7 frames)",
        "constexpr uint8_t  LOG_DLC              = 8;       // LOG frame is always 8 bytes",
        "constexpr uint8_t  LOG_TEXT_DLC         = 8;       // LOG_TEXT frame is always 8 bytes",
        "constexpr uint8_t  LOG_TEXT_MAX_FRAMES  = 7;       // Max text continuation frames",
        "constexpr uint8_t  LOG_TEXT_CHARS_PER_FRAME = 7;   // 7 ASCII chars per text frame",
        "",
    ])

    # GPS Module
    L.append("// \u2500\u2500 GPS Module \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    gps_keys = sorted(k for k in custom if custom[k]["name"].startswith("GPS_"))
    if gps_keys:
        max_name = max(len(f'CAN_ID_{custom[k]["name"]}') for k in gps_keys)
        for hex_str in gps_keys:
            msg = custom[hex_str]
            L.append(f'constexpr uint32_t {"CAN_ID_" + msg["name"]:<{max_name + 4}s} = {hex_str};  // {msg["description"]}')
    L.append("")

    # Ambient light categories
    ambient_desc = custom.get("0x726", {}).get("payload", {}).get("byte_0", "")
    if isinstance(ambient_desc, str):
        enums = parse_enum_string(ambient_desc)
        if enums:
            L.append("// Ambient light categories (byte 0 of 0x726 payload)")
            max_name = max(len(f"AMBIENT_{name}") for _, name in enums)
            for val, name in enums:
                L.append(f'constexpr uint8_t {"AMBIENT_" + name:<{max_name + 2}s} = {val};')
            L.append("")

    # Resolve EV Controller
    L.append("// \u2500\u2500 Resolve EV Controller \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    for hex_str, msg in sorted(resolve.items()):
        L.append(f'constexpr uint32_t CAN_ID_{msg["name"]} = {hex_str};')
    L.append("")

    # Leaf EV-CAN IDs
    L.append("// \u2500\u2500 Leaf EV-CAN IDs (AZE0, 2013\u20132017) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    leaf_items = sorted(leaf.items(), key=lambda x: int(x[0], 16))
    if leaf_items:
        max_name = max(len(f'CAN_ID_{msg["name"]}') for _, msg in leaf_items)
        for hex_str, msg in leaf_items:
            L.append(f'constexpr uint32_t {"CAN_ID_" + msg["name"]:<{max_name + 4}s} = {hex_str};')
    L.append("")

    # CAN bus configuration
    speed = meta["bus_speed_kbps"]
    silence = meta.get("silence_timeout_ms", 5000)
    L.extend([
        "// \u2500\u2500 CAN bus configuration \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        f"constexpr uint32_t CAN_BUS_SPEED = {speed * 1000};  // {speed} kbps",
        f"constexpr uint32_t CAN_SILENCE_TIMEOUT_MS = {silence};  // default {silence // 1000} seconds",
    ])

    return "\n".join(L) + "\n"


# ── leaf_messages.h ──────────────────────────────────────────────────────

def gen_leaf_messages_h(data):
    return gen_messages_h(
        data["leaf_ids"],
        "Leaf",
        "Leaf AZE0 CAN Message Decode Constants",
    )


# ── resolve_messages.h ───────────────────────────────────────────────────

def gen_resolve_messages_h(data):
    return gen_messages_h(
        data["resolve_ids"],
        "Resolve",
        "Resolve EV Controller CAN Message Decode Constants",
    )


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print(f"codegen: reading {JSON_PATH.relative_to(ROOT)}")
    data = load()

    targets = [
        (PY_DIR / "can_ids.py",           gen_can_ids(data)),
        (PY_DIR / "leaf_messages.py",      gen_leaf_messages(data)),
        (PY_DIR / "resolve_messages.py",   gen_resolve_messages(data)),
        (CPP_DIR / "can_ids.h",            gen_can_ids_h(data)),
        (CPP_DIR / "leaf_messages.h",      gen_leaf_messages_h(data)),
        (CPP_DIR / "resolve_messages.h",   gen_resolve_messages_h(data)),
    ]

    for path, content in targets:
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"  wrote {path.relative_to(ROOT)}")

    print("Done.")


if __name__ == "__main__":
    main()
