#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Monitor

Decoded CAN traffic viewer with contextual meaning, freshness color coding,
and filtering by module/source. Uses shared CAN definitions.

Usage: python can_monitor.py [--filter BODY,GPS,LEAF] [--interface can0]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.python import can_ids
from common.python import leaf_messages
from common.python import resolve_messages
from common.python.log_setup import setup_logging

logger = setup_logging("can-monitor")

# TODO: Import python-can
# TODO: Set up SocketCAN interface (default: can0)
# TODO: Receive loop with decoded output
# TODO: Freshness color coding (green <1s, yellow <5s, orange 10+s)
# TODO: Filter by module source (body, gps, leaf, heartbeat)
# TODO: Decode heartbeat role names and uptime
# TODO: Decode body state flags
# TODO: Decode Leaf messages via leaf_messages.DECODERS


def main():
    parser = argparse.ArgumentParser(description="CAN bus monitor with decoded output")
    parser.add_argument("--interface", default="can0", help="CAN interface (default: can0)")
    parser.add_argument("--filter", default="", help="Comma-separated module filter (BODY,GPS,LEAF,HEARTBEAT)")
    args = parser.parse_args()

    logger.critical("CAN monitor starting...")
    logger.info("Listening on %s...", args.interface)
    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
