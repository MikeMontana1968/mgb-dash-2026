"""
MGB Dash 2026 — Leaf AZE0 CAN Message Decode Constants (Python)

AUTO-GENERATED from common/can_ids.json — do not edit by hand.
Regenerate:  python tools/codegen.py

All byte offsets are 0-indexed. Multi-byte values are big-endian
unless noted otherwise.
"""

import struct


# =====================================================================
# 0x1DA — Motor RPM, torque, fail-safe status
# =====================================================================
LEAF_1DA_ID = 0x1DA

def decode_1da(data: bytes) -> dict:
    """Decode 0x1DA — Motor RPM, torque, fail-safe status."""
    available_torque_nm_raw = (data[3] << 8 | data[4]) >> 6
    available_torque_nm = available_torque_nm_raw * 0.5 - 400
    return {
        "motor_rpm": struct.unpack(">h", data[1:3])[0],
        "available_torque_nm": available_torque_nm,
        "failsafe": (data[6] >> 2) & 0x03,
    }


# =====================================================================
# 0x1DB — Battery voltage, current, SOC
# =====================================================================
LEAF_1DB_ID = 0x1DB

def decode_1db(data: bytes) -> dict:
    """Decode 0x1DB — Battery voltage, current, SOC."""
    battery_voltage_v_raw = (data[0] << 8 | data[1]) >> 6
    battery_voltage_v = battery_voltage_v_raw * 0.5
    battery_current_a_raw = (data[2] << 8 | data[3]) >> 5
    if battery_current_a_raw & 0x400:
        battery_current_a_raw -= 0x800
    battery_current_a = battery_current_a_raw * 0.5
    return {
        "battery_voltage_v": battery_voltage_v,
        "battery_current_a": battery_current_a,
        "soc_percent": data[4],
    }


# =====================================================================
# 0x1DC — Charger/OBC status and power
# =====================================================================
LEAF_1DC_ID = 0x1DC

def decode_1dc(data: bytes) -> dict:
    """Decode 0x1DC — Charger/OBC status and power."""
    charge_power_kw_raw = (data[0] << 8 | data[1]) >> 6
    charge_power_kw = charge_power_kw_raw * 0.25
    return {
        "charge_power_kw": charge_power_kw,
    }


# =====================================================================
# 0x390 — VCM operational status
# =====================================================================
LEAF_390_ID = 0x390

def decode_390(data: bytes) -> dict:
    """Decode 0x390 — VCM operational status."""
    return {
        "main_relay_closed": bool(data[4] & (1 << 0)),
    }


# =====================================================================
# 0x55A — Motor and inverter temperatures
# =====================================================================
LEAF_55A_ID = 0x55A

def decode_55a(data: bytes) -> dict:
    """Decode 0x55A — Motor and inverter temperatures."""
    motor_temp_c_raw = data[0]
    motor_temp_c = motor_temp_c_raw * 0.5
    igbt_temp_c_raw = data[1]
    igbt_temp_c = igbt_temp_c_raw * 0.5
    inverter_temp_c_raw = data[2]
    inverter_temp_c = inverter_temp_c_raw * 0.5
    return {
        "motor_temp_c": motor_temp_c,
        "igbt_temp_c": igbt_temp_c,
        "inverter_temp_c": inverter_temp_c,
    }


# =====================================================================
# 0x55B — High-precision SOC
# =====================================================================
LEAF_55B_ID = 0x55B

def decode_55b(data: bytes) -> dict:
    """Decode 0x55B — High-precision SOC."""
    soc_precise_percent_raw = struct.unpack(">H", data[0:2])[0]
    soc_precise_percent = soc_precise_percent_raw * 0.01
    return {
        "soc_precise_percent": soc_precise_percent,
    }


# =====================================================================
# 0x59E — Present only on AZE0 (2013–2017) Leaf — used for generation detection
# =====================================================================
LEAF_59E_ID = 0x59E
# No payload decode — presence on bus confirms this message


# =====================================================================
# 0x5BC — Battery capacity, SOH, GIDs
# =====================================================================
LEAF_5BC_ID = 0x5BC

def decode_5bc(data: bytes) -> dict:
    """Decode 0x5BC — Battery capacity, SOH, GIDs."""
    return {
        "gids": (data[0] << 8 | data[1]) >> 6,
        "soh_percent": (data[4] >> 1) & 0x7F,
    }


# =====================================================================
# 0x5C0 — Battery pack temperature
# =====================================================================
LEAF_5C0_ID = 0x5C0

def decode_5c0(data: bytes) -> dict:
    """Decode 0x5C0 — Battery pack temperature."""
    battery_temp_c_raw = data[0]
    if battery_temp_c_raw > 127:
        battery_temp_c_raw -= 256
    battery_temp_c = battery_temp_c_raw - 40
    return {
        "battery_temp_c": battery_temp_c,
    }


# =====================================================================
# Decoder dispatch table
# =====================================================================
DECODERS = {
    LEAF_1DA_ID: decode_1da,
    LEAF_1DB_ID: decode_1db,
    LEAF_1DC_ID: decode_1dc,
    LEAF_390_ID: decode_390,
    LEAF_55A_ID: decode_55a,
    LEAF_55B_ID: decode_55b,
    LEAF_5BC_ID: decode_5bc,
    LEAF_5C0_ID: decode_5c0,
}
