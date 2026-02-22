"""
MGB Dash 2026 — Leaf AZE0 CAN Message Decode Constants (Python)

Single source of truth: common/can_ids.json
Target: 2013 Leaf drivetrain + 2014 battery (AZE0)

All byte offsets are 0-indexed. Multi-byte values are big-endian
unless noted otherwise.
"""

import struct


# ═════════════════════════════════════════════════════════════════════
# 0x1DA — Motor Status
# ═════════════════════════════════════════════════════════════════════
LEAF_1DA_ID = 0x1DA

def decode_1da(data: bytes) -> dict:
    """Decode 0x1DA motor status message."""
    rpm = struct.unpack(">h", data[1:3])[0]  # signed 16-bit big-endian
    torque_raw = (data[3] << 8 | data[4]) >> 6  # upper 10 bits
    torque_nm = torque_raw * 0.5 - 400.0
    failsafe = (data[6] >> 2) & 0x03
    return {
        "motor_rpm": rpm,
        "available_torque_nm": torque_nm,
        "failsafe": failsafe,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x1DB — Battery Status
# ═════════════════════════════════════════════════════════════════════
LEAF_1DB_ID = 0x1DB

def decode_1db(data: bytes) -> dict:
    """Decode 0x1DB battery status message."""
    voltage_raw = (data[0] << 8 | data[1]) >> 6  # upper 10 bits
    voltage_v = voltage_raw * 0.5

    current_raw = (data[2] << 8 | data[3]) >> 5  # upper 11 bits
    # Sign-extend 11-bit value
    if current_raw & 0x400:
        current_raw -= 0x800
    current_a = current_raw * 0.5

    soc = data[4]
    return {
        "battery_voltage_v": voltage_v,
        "battery_current_a": current_a,  # positive = discharge
        "soc_percent": soc,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x55A — Inverter/Motor Temperatures
# ═════════════════════════════════════════════════════════════════════
LEAF_55A_ID = 0x55A

def decode_55a(data: bytes) -> dict:
    """Decode 0x55A inverter/motor temperatures."""
    return {
        "motor_temp_c": data[0] * 0.5,
        "igbt_temp_c": data[1] * 0.5,
        "inverter_temp_c": data[2] * 0.5,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x55B — Precise SOC
# ═════════════════════════════════════════════════════════════════════
LEAF_55B_ID = 0x55B

def decode_55b(data: bytes) -> dict:
    """Decode 0x55B precise SOC."""
    soc_raw = struct.unpack(">H", data[0:2])[0]  # unsigned 16-bit big-endian
    return {
        "soc_precise_percent": soc_raw * 0.01,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x5BC — Battery Health
# ═════════════════════════════════════════════════════════════════════
LEAF_5BC_ID = 0x5BC

def decode_5bc(data: bytes) -> dict:
    """Decode 0x5BC battery health."""
    gids = (data[0] << 8 | data[1]) >> 6  # upper 10 bits
    soh = (data[4] >> 1) & 0x7F  # bits 1–7
    return {
        "gids": gids,
        "soh_percent": soh,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x5C0 — Battery Temperature
# ═════════════════════════════════════════════════════════════════════
LEAF_5C0_ID = 0x5C0

def decode_5c0(data: bytes) -> dict:
    """Decode 0x5C0 battery temperature."""
    raw = data[0]
    if raw > 127:
        raw -= 256  # treat as signed
    temp_c = raw - 40
    return {
        "battery_temp_c": temp_c,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x1DC — Charger Status
# ═════════════════════════════════════════════════════════════════════
LEAF_1DC_ID = 0x1DC

def decode_1dc(data: bytes) -> dict:
    """Decode 0x1DC charger status."""
    power_raw = (data[0] << 8 | data[1]) >> 6  # upper 10 bits
    return {
        "charge_power_kw": power_raw * 0.25,
    }


# ═════════════════════════════════════════════════════════════════════
# 0x390 — VCM Status
# ═════════════════════════════════════════════════════════════════════
LEAF_390_ID = 0x390

def decode_390(data: bytes) -> dict:
    """Decode 0x390 VCM status."""
    return {
        "main_relay_closed": bool(data[4] & 0x01),
    }


# ═════════════════════════════════════════════════════════════════════
# 0x59E — AZE0 Identifier
# ═════════════════════════════════════════════════════════════════════
LEAF_59E_ID = 0x59E
# Presence of this ID on the bus confirms AZE0 (2013–2017)


# ═════════════════════════════════════════════════════════════════════
# Decoder dispatch table
# ═════════════════════════════════════════════════════════════════════
DECODERS = {
    LEAF_1DA_ID: decode_1da,
    LEAF_1DB_ID: decode_1db,
    LEAF_55A_ID: decode_55a,
    LEAF_55B_ID: decode_55b,
    LEAF_5BC_ID: decode_5bc,
    LEAF_5C0_ID: decode_5c0,
    LEAF_1DC_ID: decode_1dc,
    LEAF_390_ID: decode_390,
}
