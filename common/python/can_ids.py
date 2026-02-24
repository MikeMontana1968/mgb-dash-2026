"""
MGB Dash 2026 — Custom CAN Arbitration IDs (Python)

AUTO-GENERATED from common/can_ids.json — do not edit by hand.
Regenerate:  python python/tools/codegen.py
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
CAN_ID_BODY_SPEED    = 0x711  # Vehicle speed from hall sensor (authority source), 10 Hz
CAN_ID_BODY_GEAR     = 0x712  # Estimated gear from motor RPM / driveshaft RPM ratio, 2 Hz
CAN_ID_BODY_ODOMETER = 0x713  # Odometer reading, 1 Hz

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
GEAR_UNKNOWN = 0xFF
GEAR_1 = 1
GEAR_2 = 2
GEAR_3 = 3
GEAR_4 = 4

# ── Self-Test Command ──────────────────────────────────────────────
CAN_ID_SELF_TEST      = 0x730  # Triggers self-test on receiving modules. ESP32 gauges: needle sweep + LED ring pattern. Raspberry Pis: TBD display/system test.
SELF_TEST_TARGET_ALL  = 0xFF   # byte 0 = 0xFF → all modules

# ── Logging ───────────────────────────────────────────────────────────────
CAN_ID_LOG              = 0x731  # Structured log event — compact event code with context value and optional text continuation via LOG_TEXT frames
CAN_ID_LOG_TEXT         = 0x732  # Optional string continuation for LOG (0x731). Up to 7 frames = 49 ASCII characters.
LOG_DLC                 = 8      # LOG frame is always 8 bytes
LOG_TEXT_DLC            = 8      # LOG_TEXT frame is always 8 bytes
LOG_TEXT_MAX_FRAMES     = 7      # Max text continuation frames
LOG_TEXT_CHARS_PER_FRAME = 7     # 7 ASCII chars per text frame

# ── GPS Module ────────────────────────────────────────────────────────────────
CAN_ID_GPS_SPEED         = 0x720  # GPS speed
CAN_ID_GPS_TIME          = 0x721  # GPS time (seconds since midnight UTC)
CAN_ID_GPS_DATE          = 0x722  # GPS date (days since epoch 2000-01-01)
CAN_ID_GPS_LATITUDE      = 0x723  # GPS latitude
CAN_ID_GPS_LONGITUDE     = 0x724  # GPS longitude
CAN_ID_GPS_ELEVATION     = 0x725  # GPS elevation
CAN_ID_GPS_AMBIENT_LIGHT = 0x726  # Ambient light category from time relative to sunset

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

# ── Resolve EV Controller ─────────────────────────────────────────────────────
CAN_ID_RESOLVE_DISPLAY = 0x539

# ── Leaf EV-CAN IDs (AZE0, 2013–2017) ────────────────────────────────────────
CAN_ID_LEAF_MOTOR_STATUS   = 0x1DA
CAN_ID_LEAF_BATTERY_STATUS = 0x1DB
CAN_ID_LEAF_CHARGER        = 0x1DC
CAN_ID_LEAF_VCM            = 0x390
CAN_ID_LEAF_INVERTER_TEMPS = 0x55A
CAN_ID_LEAF_SOC_PRECISE    = 0x55B
CAN_ID_LEAF_AZE0_ID        = 0x59E
CAN_ID_LEAF_BATTERY_HEALTH = 0x5BC
CAN_ID_LEAF_BATTERY_TEMP   = 0x5C0

# ── CAN bus configuration ─────────────────────────────────────────────────────
CAN_BUS_SPEED = 500000  # 500 kbps
