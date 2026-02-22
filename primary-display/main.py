"""
MGB Dash 2026 — Primary Display (Pi 4B)

Qt/QML + PySide6 dashboard on Waveshare 3.4" Round DSI LCD (800x800).
Reads CAN bus, monitors heartbeats, drives context-driven display.

Contexts: Startup, Driving, Charging, Idle, Diagnostics
"""

import sys
import os

# Add common/ to path for shared CAN definitions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.python import can_ids
from common.python import leaf_messages

# TODO: Import PySide6 / Qt Quick
# TODO: Import python-can
# TODO: Set up CAN bus listener (Innomaker USB2CAN, gs_usb/SocketCAN)
# TODO: Heartbeat monitor — track all module heartbeats, alert on timeout
# TODO: Context state machine (Startup → Idle ↔ Driving ↔ Charging ↔ Diagnostics)
# TODO: QML engine setup with eglfs direct rendering
# TODO: CAN data → QML property bridge
# TODO: UDS polling for cell voltages (0x79B/0x7BB) in detailed charging view


def main():
    print(f"[DASH] Primary display starting...")
    print(f"[DASH] CAN bus speed: {can_ids.CAN_BUS_SPEED} bps")
    print(f"[DASH] Heartbeat ID: 0x{can_ids.CAN_ID_HEARTBEAT:03X}")

    # TODO: Initialize Qt application
    # TODO: Load QML UI
    # TODO: Start CAN listener thread
    # TODO: Start heartbeat monitor
    # TODO: Enter Qt event loop

    print("[DASH] Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
