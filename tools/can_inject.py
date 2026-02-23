#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Inject

Send single CAN frames manually for testing.

Usage: python can_inject.py --id 0x710 --data "01 00 00 00 00 00 00 00"
       python can_inject.py --id 0x700 --data "46 55 45 4C 20 0A 00 00"
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-inject")

# TODO: Import python-can
# TODO: Parse hex data string into bytes
# TODO: Send single CAN frame
# TODO: Print confirmation with decoded meaning


def main():
    parser = argparse.ArgumentParser(description="Send a single CAN frame")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    parser.add_argument("--id", required=True, help="CAN ID in hex (e.g., 0x710)")
    parser.add_argument("--data", required=True, help="Payload bytes in hex (e.g., '01 00 00 00 00 00 00 00')")
    args = parser.parse_args()

    logger.critical("CAN inject starting...")
    logger.info("Sending 0x%03X on %s...", int(args.id, 16), args.interface)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
