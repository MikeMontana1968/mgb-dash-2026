#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Replay

Record and playback CAN bus sessions with timestamps.

Usage: python can_replay.py record --output session.canlog
       python can_replay.py play --input session.canlog [--speed 2.0]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-replay")

# TODO: Import python-can
# TODO: Record mode: capture all CAN frames with timestamps to file
# TODO: Play mode: replay frames with original timing (adjustable speed)
# TODO: File format: timestamp_ms, id_hex, dlc, data_hex per line


def main():
    parser = argparse.ArgumentParser(description="Record and replay CAN bus sessions")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    subparsers = parser.add_subparsers(dest="command")

    rec = subparsers.add_parser("record", help="Record CAN traffic")
    rec.add_argument("--output", required=True, help="Output file path")

    play = subparsers.add_parser("play", help="Replay recorded traffic")
    play.add_argument("--input", required=True, help="Input file path")
    play.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier")

    args = parser.parse_args()

    logger.critical("CAN replay starting...")
    logger.info("%s on %s...", args.command or "no command", args.interface)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
