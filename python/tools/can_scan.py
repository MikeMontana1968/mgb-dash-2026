#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Scan

Bus discovery: detect Leaf generation (check for 0x59E = AZE0),
report present/missing modules via heartbeat monitoring.

Usage: python can_scan.py [--interface can0] [--timeout 5]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-scan")

# TODO: Import python-can
# TODO: Listen for 0x59E to confirm AZE0 (2013–2017) Leaf
# TODO: Monitor heartbeat ID (0x700) for module role names
# TODO: Report which modules are present/missing after timeout
# TODO: Report any unexpected CAN IDs seen on the bus


def main():
    parser = argparse.ArgumentParser(description="CAN bus scanner and module discovery")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    parser.add_argument("--timeout", type=int, default=5, help="Scan duration in seconds (default: 5)")
    args = parser.parse_args()

    logger.critical("CAN scan starting...")
    logger.info("Scanning %s for %ds...", args.interface, args.timeout)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
