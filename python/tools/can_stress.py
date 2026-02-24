#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Stress Test

Bus load testing at configurable rates.

Usage: python can_stress.py --rate 1000 --duration 10
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-stress")

# TODO: Import python-can
# TODO: Send CAN frames at specified rate (frames/sec)
# TODO: Measure actual throughput and error rate
# TODO: Report bus load percentage


def main():
    parser = argparse.ArgumentParser(description="CAN bus stress test")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    parser.add_argument("--rate", type=int, default=1000, help="Frames per second (default: 1000)")
    parser.add_argument("--duration", type=int, default=10, help="Duration in seconds (default: 10)")
    args = parser.parse_args()

    logger.critical("CAN stress test starting...")
    logger.info("%d fps for %ds on %s...", args.rate, args.duration, args.interface)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
