"""MGB Dash 2026 — DataSource ABC with shared CAN decode routing."""

import abc
import struct
from vehicle_state import VehicleState
from common.python import can_ids, leaf_messages, resolve_messages


class DataSource(abc.ABC):
    """Pluggable CAN data producer. Subclasses call _decode_and_store()
    to route raw CAN frames through the shared decode pipeline."""

    def __init__(self, state: VehicleState):
        self._state = state

    @abc.abstractmethod
    def start(self):
        """Begin producing data (usually starts a daemon thread)."""

    @abc.abstractmethod
    def stop(self):
        """Stop producing data and clean up."""

    def _decode_and_store(self, arb_id: int, data: bytes):
        """Decode a CAN frame and store results in VehicleState."""
        self._state.update_raw(arb_id, data)

        # ── Leaf EV-CAN ──────────────────────────────────────────────
        if arb_id in leaf_messages.DECODERS:
            decoded = leaf_messages.DECODERS[arb_id](data)
            self._state.update_signals(decoded)
            return

        # ── Resolve EV Controller ────────────────────────────────────
        if arb_id == can_ids.CAN_ID_RESOLVE_DISPLAY:
            decoded = resolve_messages.decode_539(data)
            prefixed = {f"resolve_{k}": v for k, v in decoded.items()}
            self._state.update_signals(prefixed)
            return

        # ── Heartbeat ────────────────────────────────────────────────
        if arb_id == can_ids.CAN_ID_HEARTBEAT:
            role = data[0:5].decode("ascii", errors="replace").strip()
            counter = data[5]
            error_flags = data[6]
            self._state.update_heartbeat(role, counter, error_flags)
            return

        # ── Body state flags ─────────────────────────────────────────
        if arb_id == can_ids.CAN_ID_BODY_STATE:
            flags = data[0]
            self._state.update_signals({
                "key_on":      bool(flags & can_ids.BODY_FLAG_KEY_ON),
                "brake":       bool(flags & can_ids.BODY_FLAG_BRAKE),
                "regen":       bool(flags & can_ids.BODY_FLAG_REGEN),
                "fan":         bool(flags & can_ids.BODY_FLAG_FAN),
                "reverse":     bool(flags & can_ids.BODY_FLAG_REVERSE),
                "left_turn":   bool(flags & can_ids.BODY_FLAG_LEFT_TURN),
                "right_turn":  bool(flags & can_ids.BODY_FLAG_RIGHT_TURN),
                "hazard":      bool(flags & can_ids.BODY_FLAG_HAZARD),
            })
            return

        # ── Body speed (64-bit double) ───────────────────────────────
        if arb_id == can_ids.CAN_ID_BODY_SPEED:
            speed = struct.unpack("<d", data[0:8])[0]
            self._state.update_signals({"body_speed_mph": speed})
            return

        # ── Body gear ────────────────────────────────────────────────
        if arb_id == can_ids.CAN_ID_BODY_GEAR:
            self._state.update_signals({
                "body_gear": data[0],
                "body_reverse": bool(data[1]),
            })
            return

        # ── Body odometer (32-bit LE unsigned) ───────────────────────
        if arb_id == can_ids.CAN_ID_BODY_ODOMETER:
            odometer = struct.unpack("<I", data[0:4])[0]
            self._state.update_signals({"odometer_miles": odometer})
            return

        # ── GPS doubles ──────────────────────────────────────────────
        _gps_doubles = {
            can_ids.CAN_ID_GPS_SPEED:     "gps_speed_mph",
            can_ids.CAN_ID_GPS_TIME:      "gps_time_utc_s",
            can_ids.CAN_ID_GPS_DATE:      "gps_date_days",
            can_ids.CAN_ID_GPS_LATITUDE:  "gps_latitude",
            can_ids.CAN_ID_GPS_LONGITUDE: "gps_longitude",
            can_ids.CAN_ID_GPS_ELEVATION: "gps_elevation_m",
        }
        if arb_id in _gps_doubles:
            value = struct.unpack("<d", data[0:8])[0]
            self._state.update_signals({_gps_doubles[arb_id]: value})
            return

        # ── GPS ambient light ────────────────────────────────────────
        if arb_id == can_ids.CAN_ID_GPS_AMBIENT_LIGHT:
            cat = data[0]
            name = can_ids.AMBIENT_NAMES.get(cat, f"UNKNOWN({cat})")
            self._state.update_signals({
                "ambient_light": cat,
                "ambient_light_name": name,
            })
            return
