"""
MGB Dash 2026 — Custom CAN Arbitration IDs (Python)

Single source of truth: common/can_ids.json
This file is a manually-maintained Python mirror.
"""

# ── Custom CAN ID range ──────────────────────────────────────────────
CAN_CUSTOM_ID_MIN = 0x700
CAN_CUSTOM_ID_MAX = 0x73F

# ── Heartbeat (all modules) ─────────────────────────────────────────
CAN_ID_HEARTBEAT = 0x700
HEARTBEAT_LEN = 8
HEARTBEAT_INTERVAL_S = 1.0

# Heartbeat role names — 5 bytes, space-padded
ROLE_FUEL  = b"FUEL "
ROLE_AMPS  = b"AMPS "
ROLE_TEMP  = b"TEMP "
ROLE_SPEED = b"SPEED"
ROLE_BODY  = b"BODY "
ROLE_DASH  = b"DASH "
ROLE_GPS   = b"GPS  "

ALL_ROLES = [ROLE_FUEL, ROLE_AMPS, ROLE_TEMP, ROLE_SPEED, ROLE_BODY, ROLE_DASH, ROLE_GPS]

# Heartbeat payload byte offsets
HB_ROLE_OFFSET = 0      # bytes 0–4: role name
HB_ROLE_LEN = 5
HB_UPTIME_OFFSET = 5    # byte 5: rolling counter 0–255
HB_ERROR_OFFSET = 6     # byte 6: error flags bitfield
HB_RESERVED_OFFSET = 7  # byte 7: reserved (0x00)

# ── Body Controller ─────────────────────────────────────────────────
CAN_ID_BODY_STATE    = 0x710  # Vehicle state bit flags, 10 Hz
CAN_ID_BODY_SPEED    = 0x711  # Speed (64-bit double, mph)
CAN_ID_BODY_GEAR     = 0x712  # Estimated gear
CAN_ID_BODY_ODOMETER = 0x713  # Odometer (uint32, miles)

# Body state bit flags (byte 0 of 0x710 payload)
BODY_FLAG_KEY_ON     = 1 << 0
BODY_FLAG_BRAKE      = 1 << 1
BODY_FLAG_REGEN      = 1 << 2
BODY_FLAG_FAN        = 1 << 3
BODY_FLAG_REVERSE    = 1 << 4
BODY_FLAG_LEFT_TURN  = 1 << 5
BODY_FLAG_RIGHT_TURN = 1 << 6
BODY_FLAG_HAZARD     = 1 << 7

# Gear values (byte 0 of 0x712 payload)
GEAR_NEUTRAL = 0
GEAR_1 = 1
GEAR_2 = 2
GEAR_3 = 3
GEAR_4 = 4
GEAR_UNKNOWN = 0xFF

# ── Self-Test Command ──────────────────────────────────────────────
CAN_ID_SELF_TEST      = 0x730  # On-demand self-test trigger
SELF_TEST_TARGET_ALL  = 0xFF   # byte 0 = 0xFF → all modules

# ── Logging ───────────────────────────────────────────────────────
CAN_ID_LOG              = 0x731  # Structured log event
CAN_ID_LOG_TEXT         = 0x732  # Log text continuation (up to 7 frames)
LOG_DLC                 = 8      # LOG frame is always 8 bytes
LOG_TEXT_DLC            = 8      # LOG_TEXT frame is always 8 bytes
LOG_TEXT_MAX_FRAMES     = 7      # Max text continuation frames
LOG_TEXT_CHARS_PER_FRAME = 7     # 7 ASCII chars per text frame

# ── GPS Module ──────────────────────────────────────────────────────
CAN_ID_GPS_SPEED         = 0x720  # Speed (64-bit double, mph)
CAN_ID_GPS_TIME          = 0x721  # Seconds since midnight UTC
CAN_ID_GPS_DATE          = 0x722  # Days since 2000-01-01
CAN_ID_GPS_LATITUDE      = 0x723  # Decimal degrees
CAN_ID_GPS_LONGITUDE     = 0x724  # Decimal degrees
CAN_ID_GPS_ELEVATION     = 0x725  # Meters above sea level
CAN_ID_GPS_AMBIENT_LIGHT = 0x726  # 0–3 category

# Ambient light categories
AMBIENT_DAYLIGHT       = 0
AMBIENT_EARLY_TWILIGHT = 1
AMBIENT_LATE_TWILIGHT  = 2
AMBIENT_DARKNESS       = 3

AMBIENT_NAMES = {
    AMBIENT_DAYLIGHT: "DAYLIGHT",
    AMBIENT_EARLY_TWILIGHT: "EARLY_TWILIGHT",
    AMBIENT_LATE_TWILIGHT: "LATE_TWILIGHT",
    AMBIENT_DARKNESS: "DARKNESS",
}

# ── Resolve EV Controller ───────────────────────────────────────────
CAN_ID_RESOLVE_DISPLAY = 0x539

# ── Leaf EV-CAN IDs (AZE0, 2013–2017) ──────────────────────────────
CAN_ID_LEAF_MOTOR_STATUS   = 0x1DA
CAN_ID_LEAF_BATTERY_STATUS = 0x1DB
CAN_ID_LEAF_CHARGER        = 0x1DC
CAN_ID_LEAF_VCM            = 0x390
CAN_ID_LEAF_INVERTER_TEMPS = 0x55A
CAN_ID_LEAF_SOC_PRECISE    = 0x55B
CAN_ID_LEAF_BATTERY_HEALTH = 0x5BC
CAN_ID_LEAF_BATTERY_TEMP   = 0x5C0
CAN_ID_LEAF_AZE0_ID        = 0x59E

# ── CAN bus configuration ───────────────────────────────────────────
CAN_BUS_SPEED = 500000  # 500 kbps
