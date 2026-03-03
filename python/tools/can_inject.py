#!/usr/bin/env python3
"""
MGB Dash 2026 — CAN Inject

Send single CAN frames manually for testing.

Usage:
  python can_inject.py --id 0x710 --data "01 00 00 00 00 00 00 00"
  python can_inject.py --id 0x710 --data 0100000000000000
  python can_inject.py --self-test
  python can_inject.py --self-test --target FUEL
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import can

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("can-inject")

SELF_TEST_TARGETS = {
    "ALL": 0xFF, "FUEL": 0x46, "AMPS": 0x41, "TEMP": 0x54,
    "SPEED": 0x53, "BODY": 0x42, "DASH": 0x44, "GPS": 0x47,
}


def parse_hex_data(data_str):
    """Parse hex data string — supports '01 02 03' and '010203' formats."""
    data_str = data_str.strip()
    if " " in data_str:
        return bytes(int(b, 16) for b in data_str.split())
    else:
        return bytes.fromhex(data_str)


def main():
    parser = argparse.ArgumentParser(description="Send a single CAN frame")
    parser.add_argument("--interface", default="can0",
                        help="CAN interface (default: can0)")
    parser.add_argument("--id", default=None,
                        help="CAN ID in hex (e.g., 0x710)")
    parser.add_argument("--data", default=None,
                        help="Payload bytes in hex (e.g., '01 02 03' or '010203')")
    parser.add_argument("--self-test", action="store_true",
                        help="Send self-test frame (0x730 FF)")
    parser.add_argument("--target", default="ALL",
                        help="Self-test target (ALL, FUEL, AMPS, TEMP, SPEED, BODY, DASH, GPS)")
    args = parser.parse_args()

    # Validate arguments
    if args.self_test:
        if args.id or args.data:
            parser.error("--self-test cannot be combined with --id/--data")
        target_name = args.target.upper()
        if target_name not in SELF_TEST_TARGETS:
            parser.error(f"Unknown target: {args.target} "
                         f"(valid: {', '.join(SELF_TEST_TARGETS.keys())})")
        arb_id = can_ids.CAN_ID_SELF_TEST
        data = bytes([SELF_TEST_TARGETS[target_name]] + [0x00] * 7)
    else:
        if not args.id or not args.data:
            parser.error("--id and --data are required (or use --self-test)")
        arb_id = int(args.id, 16)
        data = parse_hex_data(args.data)

    logger.critical("CAN inject: 0x%03X [%d] %s on %s",
                    arb_id, len(data),
                    " ".join(f"{b:02X}" for b in data),
                    args.interface)

    try:
        bus = can.Bus(interface="socketcan", channel=args.interface,
                      bitrate=can_ids.CAN_BUS_SPEED)
    except Exception as e:
        logger.error("Failed to open %s: %s", args.interface, e)
        sys.exit(1)

    try:
        msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
        bus.send(msg)
        print(f"Sent: 0x{arb_id:03X} [{len(data)}] "
              f"{' '.join(f'{b:02X}' for b in data)}")
    except Exception as e:
        logger.error("Send failed: %s", e)
        sys.exit(1)
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
