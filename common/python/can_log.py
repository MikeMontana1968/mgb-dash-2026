"""
MGB Dash 2026 — CAN Log Module (Python)

Structured log events over CAN bus (0x731 LOG, 0x732 LOG_TEXT).
Mirrors common/cpp/log_events.h enums and common/cpp/CanLog behavior.

Usage:
    from common.python.can_log import LogLevel, LogRole, LogEvent, can_log
    can_log(bus, LogRole.DASH, LogLevel.INFO, LogEvent.BOOT_START)
    can_log(None, LogRole.DASH, LogLevel.WARN, LogEvent.LOW_VOLTAGE, context=11200, text="11.2V")
"""

import struct
import logging
from enum import IntEnum

from .can_ids import (
    CAN_ID_LOG,
    CAN_ID_LOG_TEXT,
    LOG_DLC,
    LOG_TEXT_DLC,
    LOG_TEXT_MAX_FRAMES,
    LOG_TEXT_CHARS_PER_FRAME,
)

logger = logging.getLogger("mgb.canlog")


# ── Enums (mirror C++ log_events.h exactly) ─────────────────────────

class LogLevel(IntEnum):
    LOG_DEBUG    = 0
    LOG_INFO     = 1
    LOG_WARN     = 2
    LOG_ERROR    = 3
    LOG_CRITICAL = 4


class LogRole(IntEnum):
    FUEL  = 0
    AMPS  = 1
    TEMP  = 2
    SPEED = 3
    BODY  = 4
    DASH  = 5
    GPS   = 6


class LogEvent(IntEnum):
    # Boot / Init (0x00–0x0F)
    BOOT_START       = 0x00
    BOOT_COMPLETE    = 0x01
    CAN_INIT_OK      = 0x02
    CAN_INIT_FAIL    = 0x03
    WIFI_OK          = 0x04
    WIFI_FAIL        = 0x05
    BLE_OK           = 0x06
    BLE_FAIL         = 0x07

    # CAN Health (0x10–0x1F)
    BUS_ERROR        = 0x10
    BUS_OFF          = 0x11
    BUS_RECOVERED    = 0x12
    TX_FAIL          = 0x13
    RX_OVERFLOW      = 0x14

    # Self-Test (0x20–0x2F)
    SELF_TEST_START  = 0x20
    SELF_TEST_PASS   = 0x21
    SELF_TEST_FAIL   = 0x22

    # Sensor / Gauge (0x30–0x3F)
    SENSOR_OUT_OF_RANGE = 0x30
    SENSOR_TIMEOUT      = 0x31
    SERVO_LIMIT         = 0x32
    SERVO_STALL         = 0x33
    STEPPER_HOME_OK     = 0x34
    STEPPER_HOME_FAIL   = 0x35

    # Comms (0x40–0x4F)
    HEARTBEAT_TIMEOUT  = 0x40
    HEARTBEAT_RESUMED  = 0x41
    BLE_CONNECT        = 0x42
    BLE_DISCONNECT     = 0x43
    GPS_FIX_ACQUIRED   = 0x44
    GPS_FIX_LOST       = 0x45
    CAN_SILENCE        = 0x46

    # Power (0x50–0x5F)
    KEY_ON             = 0x50
    KEY_OFF            = 0x51
    LOW_VOLTAGE        = 0x52
    OVERTEMP           = 0x53

    # Display (0x60–0x6F)
    DISPLAY_INIT_OK    = 0x60
    DISPLAY_INIT_FAIL  = 0x61
    EINK_REFRESH       = 0x62
    EINK_FAIL          = 0x63

    # Generic (0xF0–0xFF)
    GENERIC_INFO       = 0xF0
    GENERIC_WARN       = 0xF1
    GENERIC_ERROR      = 0xF2
    WATCHDOG_RESET     = 0xFD
    ASSERT_FAILED      = 0xFE
    UNKNOWN            = 0xFF


# ── Pack / Unpack Helpers ────────────────────────────────────────────

def pack_role_level(role: LogRole, level: LogLevel) -> int:
    """Pack role (high nibble) and level (low nibble) into a single byte."""
    return ((int(role) & 0x0F) << 4) | (int(level) & 0x0F)


def unpack_role_level(byte0: int) -> tuple:
    """Unpack (LogRole, LogLevel) from byte 0."""
    return LogRole((byte0 >> 4) & 0x0F), LogLevel(byte0 & 0x0F)


# ── Frame Compose / Decode ───────────────────────────────────────────

def compose_log_frame(role: LogRole, level: LogLevel, event: LogEvent,
                      context: int = 0, text_frames: int = 0) -> bytes:
    """Build the 8-byte LOG (0x731) payload."""
    return struct.pack(
        ">BBIBB",
        pack_role_level(role, level),
        int(event),
        context & 0xFFFFFFFF,
        0x00,           # reserved
        text_frames & 0x07,
    )


def decode_log_frame(data: bytes) -> dict:
    """Decode an 8-byte LOG (0x731) payload into a dict."""
    if len(data) < LOG_DLC:
        raise ValueError(f"LOG frame must be {LOG_DLC} bytes, got {len(data)}")
    role_level, event_code, context, _reserved, text_frames = struct.unpack(">BBIBB", data[:8])
    role, level = unpack_role_level(role_level)
    return {
        "role": role,
        "level": level,
        "event": LogEvent(event_code),
        "context": context,
        "text_frames": text_frames,
    }


def compose_text_frame(index: int, text_chunk: str) -> bytes:
    """Build an 8-byte LOG_TEXT (0x732) payload for a single fragment."""
    payload = bytearray(LOG_TEXT_DLC)
    payload[0] = index & 0xFF
    encoded = text_chunk.encode("ascii", errors="replace")[:LOG_TEXT_CHARS_PER_FRAME]
    payload[1:1 + len(encoded)] = encoded
    return bytes(payload)


def decode_text_frame(data: bytes) -> tuple:
    """Decode an 8-byte LOG_TEXT (0x732) payload. Returns (index, text_chunk)."""
    if len(data) < LOG_TEXT_DLC:
        raise ValueError(f"LOG_TEXT frame must be {LOG_TEXT_DLC} bytes, got {len(data)}")
    index = data[0]
    text_chunk = data[1:8].split(b"\x00", 1)[0].decode("ascii", errors="replace")
    return index, text_chunk


# ── High-Level Send ──────────────────────────────────────────────────

def can_log(bus, role: LogRole, level: LogLevel, event: LogEvent,
            context: int = 0, text: str = None, min_level: LogLevel = LogLevel.LOG_DEBUG):
    """
    Send a structured log event over CAN bus.

    If bus is None, falls back to Python logging module.
    The `import can` is deferred to avoid import errors when python-can
    is not installed.

    Args:
        bus:        python-can Bus instance, or None for logging fallback
        role:       Module role
        level:      Log severity
        event:      Event code
        context:    Optional uint32 context value
        text:       Optional text message (up to 49 chars)
        min_level:  Minimum level to emit (default DEBUG)
    """
    if int(level) < int(min_level):
        return

    # Calculate text frames
    text_frames = 0
    if text:
        text_frames = (len(text) + LOG_TEXT_CHARS_PER_FRAME - 1) // LOG_TEXT_CHARS_PER_FRAME
        if text_frames > LOG_TEXT_MAX_FRAMES:
            text_frames = LOG_TEXT_MAX_FRAMES

    if bus is None:
        # Fallback to Python logging
        _logging_fallback(role, level, event, context, text)
        return

    import can  # deferred import

    # Send LOG frame
    log_payload = compose_log_frame(role, level, event, context, text_frames)
    bus.send(can.Message(arbitration_id=CAN_ID_LOG, data=log_payload, is_extended_id=False))

    # Send text continuation frames
    if text and text_frames > 0:
        for i in range(text_frames):
            offset = i * LOG_TEXT_CHARS_PER_FRAME
            chunk = text[offset:offset + LOG_TEXT_CHARS_PER_FRAME]
            text_payload = compose_text_frame(i, chunk)
            bus.send(can.Message(arbitration_id=CAN_ID_LOG_TEXT, data=text_payload, is_extended_id=False))


# ── Logging Fallback ─────────────────────────────────────────────────

_LEVEL_TO_LOGGING = {
    LogLevel.LOG_DEBUG:    logging.DEBUG,
    LogLevel.LOG_INFO:     logging.INFO,
    LogLevel.LOG_WARN:     logging.WARNING,
    LogLevel.LOG_ERROR:    logging.ERROR,
    LogLevel.LOG_CRITICAL: logging.CRITICAL,
}


def _logging_fallback(role: LogRole, level: LogLevel, event: LogEvent,
                      context: int, text: str):
    """Emit log event via Python logging when CAN bus is unavailable."""
    py_level = _LEVEL_TO_LOGGING.get(level, logging.INFO)
    msg = f"[{role.name}] {event.name} ctx={context}"
    if text:
        msg += f" {text}"
    logger.log(py_level, msg)
