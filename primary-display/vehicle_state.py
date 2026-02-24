"""MGB Dash 2026 — Thread-safe central data model for all CAN signals."""

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SignalValue:
    """A single decoded CAN signal with timestamp."""
    value: Any
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.timestamp


@dataclass
class HeartbeatInfo:
    """Heartbeat status for a module."""
    role: str
    counter: int
    error_flags: int
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.timestamp


class VehicleState:
    """Central data model. CAN listener threads write, main loop reads.

    Single coarse lock — write rate ~50 msg/sec, read rate ~10 Hz = zero contention.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._signals: Dict[str, SignalValue] = {}
        self._heartbeats: Dict[str, HeartbeatInfo] = {}
        self._raw_frames: Dict[int, tuple] = {}   # arb_id -> (data_bytes, timestamp)

    def update_signals(self, decoded: dict):
        """Batch update from a decoded CAN message."""
        now = time.monotonic()
        with self._lock:
            for key, value in decoded.items():
                self._signals[key] = SignalValue(value=value, timestamp=now)

    def update_heartbeat(self, role: str, counter: int, error_flags: int):
        now = time.monotonic()
        with self._lock:
            self._heartbeats[role] = HeartbeatInfo(
                role=role, counter=counter, error_flags=error_flags, timestamp=now
            )

    def update_raw(self, arb_id: int, data: bytes):
        now = time.monotonic()
        with self._lock:
            self._raw_frames[arb_id] = (bytes(data), now)

    def get_all_signals(self) -> Dict[str, SignalValue]:
        """Snapshot copy of all signals — safe to use outside lock."""
        with self._lock:
            return dict(self._signals)

    def get_heartbeats(self) -> Dict[str, HeartbeatInfo]:
        with self._lock:
            return dict(self._heartbeats)

    def get_raw_frames(self) -> Dict[int, tuple]:
        with self._lock:
            return dict(self._raw_frames)
