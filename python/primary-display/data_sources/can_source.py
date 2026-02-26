"""MGB Dash 2026 — CanBusSource: real CAN data via SocketCAN."""

import logging

from .base import DataSource
from vehicle_state import VehicleState
from common.python.can_listener import CanListener

logger = logging.getLogger("mgb.dash")


class CanBusSource(DataSource):
    """Reads live CAN frames from SocketCAN (can0) via shared CanListener.

    All decode routing is inherited from DataSource._decode_and_store().
    Non-fatal if can0 is unavailable — logs error and returns cleanly.
    """

    def __init__(self, state: VehicleState):
        super().__init__(state)
        self._bus = None
        self._listener = None

    def start(self):
        import can

        try:
            self._bus = can.Bus(channel="can0", interface="socketcan")
            logger.info("CAN bus initialized on can0")
        except Exception as e:
            logger.error("CAN bus init failed: %s", e)
            return

        self._listener = CanListener(
            self._bus, role_char=ord("D"), logger=logger
        )
        self._listener.on_any_message(self._on_frame)
        self._listener.on_self_test(self._on_self_test)
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
        if self._bus:
            self._bus.shutdown()
            logger.info("CAN bus shut down")

    def _on_frame(self, arb_id: int, data: bytes):
        self._decode_and_store(arb_id, data)

    def _on_self_test(self, arb_id: int, data: bytes):
        logger.info("Self-test received (0x%03X, data=%s)", arb_id, data.hex())
