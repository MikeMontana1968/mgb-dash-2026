"""
MGB Dash 2026 — Resolve EV Controller CAN Message Decode Constants (Python)

Single source of truth: common/can_ids.json
Resolve EV Controller broadcasts 0x539 with display info.
"""

RESOLVE_539_ID = 0x539


def decode_539(data: bytes) -> dict:
    """Decode 0x539 Resolve EV display message."""
    gear = data[0] & 0x0F
    ignition_on = bool(data[0] & (1 << 4))
    system_on = bool(data[0] & (1 << 5))
    display_max_charge = bool(data[0] & (1 << 6))
    regen_strength = data[1]
    soc = data[2]
    return {
        "gear": gear,
        "ignition_on": ignition_on,
        "system_on": system_on,
        "display_max_charge_on": display_max_charge,
        "regen_strength": regen_strength,
        "soc_percent": soc,
    }
