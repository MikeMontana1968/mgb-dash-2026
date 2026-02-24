#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Emulator

Emulate any module's CAN output with configurable values and scripted scenarios.

Usage: python can_emulate.py --module leaf [--interface can0]
       python can_emulate.py --module body --speed 45.0
       python can_emulate.py --module gps --lat 40.7128 --lon -74.0060
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-emulate")

# TODO: Import python-can
# TODO: Emulate Leaf CAN messages (0x1DA, 0x1DB, etc.) with configurable values
# TODO: Emulate body controller messages (speed, gear, state flags, odometer)
# TODO: Emulate GPS messages (speed, time, date, lat, lon, elevation, ambient)
# TODO: Emulate heartbeats from any/all modules
# TODO: Support scripted scenarios (e.g., "drive cycle", "charging session")


def main():
    parser = argparse.ArgumentParser(description="CAN bus module emulator")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    parser.add_argument("--module", required=True, choices=["leaf", "body", "gps", "heartbeat", "all"],
                        help="Module to emulate")
    args = parser.parse_args()

    logger.critical("CAN emulator starting...")
    logger.info("Emulating %s on %s...", args.module, args.interface)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
