"""
MGB Dash 2026 — Resolve EV Controller CAN Message Decode Constants (Python)

AUTO-GENERATED from common/can_ids.json — do not edit by hand.
Regenerate:  python tools/codegen.py
"""

RESOLVE_539_ID = 0x539


def decode_539(data: bytes) -> dict:
    """Decode 0x539 — Resolve EV Controller display message."""
    return {
        "gear": data[0] & 0x0F,
        "ignition_on": bool(data[0] & (1 << 4)),
        "system_on": bool(data[0] & (1 << 5)),
        "display_max_charge_on": bool(data[0] & (1 << 6)),
        "regen_strength": data[1],
        "soc_percent": data[2],
    }
