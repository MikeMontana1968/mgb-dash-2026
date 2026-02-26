"""
MGB Dash 2026 — Shared CAN Listener (threaded receiver with callback dispatch)

Used by both GPS display and primary display to receive CAN frames.

Usage:
    from common.python.can_listener import CanListener

    listener = CanListener(bus, role_char=ord('G'), logger=logger)
    listener.on_message(0x710, handle_body_state)
    listener.on_any_message(handle_frame)
    listener.on_self_test(handle_self_test)
    listener.start()
    ...
    listener.stop()
"""

import threading

from .can_ids import CAN_ID_SELF_TEST, SELF_TEST_TARGET_ALL


class CanListener:
    """Threaded CAN receiver with callback dispatch.

    Args:
        bus:        python-can Bus instance
        role_char:  single byte identifying this module for self-test targeting
                    (e.g. ord('G') for GPS, ord('D') for Dash)
        logger:     Python logger instance
    """

    def __init__(self, bus, role_char: int, logger):
        self._bus = bus
        self._role_char = role_char
        self._logger = logger
        self._running = False
        self._thread = None
        self._handlers = {}       # arb_id -> list[callback(arb_id, data)]
        self._any_handlers = []   # list[callback(arb_id, data)]
        self._self_test_cb = None

    def on_message(self, arb_id: int, callback):
        """Register a handler for a specific arbitration ID."""
        self._handlers.setdefault(arb_id, []).append(callback)

    def on_any_message(self, callback):
        """Register a catch-all handler (fires for every non-self-test frame)."""
        self._any_handlers.append(callback)

    def on_self_test(self, callback):
        """Register the self-test handler. Receives (arb_id, data)."""
        self._self_test_cb = callback

    def start(self):
        """Spawn the receive daemon thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="can-listener"
        )
        self._thread.start()

    def stop(self):
        """Signal the thread to stop and wait for it."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        """Receive loop: poll bus with short timeout, dispatch callbacks."""
        self._logger.info("CAN listener started (role_char=0x%02X)", self._role_char)
        while self._running:
            try:
                msg = self._bus.recv(timeout=0.1)
                if msg is None:
                    continue

                arb_id = msg.arbitration_id
                data = bytes(msg.data)

                # Self-test intercept: check target byte
                if arb_id == CAN_ID_SELF_TEST:
                    if len(data) >= 1:
                        target = data[0]
                        if target == SELF_TEST_TARGET_ALL or target == self._role_char:
                            if self._self_test_cb:
                                try:
                                    self._self_test_cb(arb_id, data)
                                except Exception as e:
                                    self._logger.error("Self-test callback error: %s", e)
                    continue  # self-test is NOT forwarded to other handlers

                # Specific handlers
                if arb_id in self._handlers:
                    for cb in self._handlers[arb_id]:
                        try:
                            cb(arb_id, data)
                        except Exception as e:
                            self._logger.error("Handler error (0x%03X): %s", arb_id, e)

                # Catch-all handlers
                for cb in self._any_handlers:
                    try:
                        cb(arb_id, data)
                    except Exception as e:
                        self._logger.error("Catch-all handler error (0x%03X): %s", arb_id, e)

            except Exception as e:
                if self._running:
                    self._logger.error("CAN receive error: %s", e)

        self._logger.info("CAN listener stopped")
