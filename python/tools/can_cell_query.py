#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Cell Query

UDS query for Leaf battery cell voltages, shunt status, and temperatures.
Uses 0x79B (request) / 0x7BB (response), Group 0x02 + 0x06.

Usage: python can_cell_query.py [--interface can0] [--interval 30]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-cell-query")

# TODO: Import python-can
# TODO: Send UDS request to 0x79B (BMS diagnostic request)
# TODO: Receive multi-frame response on 0x7BB
# TODO: Decode 96 cell pair voltages (Group 0x02)
# TODO: Decode shunt status (Group 0x06)
# TODO: Display cell min/max/delta, flag imbalanced cells
# TODO: Optional: periodic polling at configurable interval


def main():
    parser = argparse.ArgumentParser(description="Leaf battery cell voltage query")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    parser.add_argument("--interval", type=int, default=0, help="Poll interval in seconds (0 = once)")
    args = parser.parse_args()

    logger.critical("CAN cell query starting...")
    logger.info("Querying cells on %s...", args.interface)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
