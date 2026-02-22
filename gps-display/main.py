"""
MGB Dash 2026 — GPS Display (Pi 3B)

Waveshare 2" Round LCD with NEO-6M GPS receiver.
Broadcasts GPS data on CAN, displays 24hr clock with moon phase.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.python import can_ids

# TODO: Import python-can
# TODO: Import serial (for GPS UART at 9600 baud)
# TODO: Import ephem or astral (for sunrise/sunset/moon calculations)
# TODO: Import display library for Waveshare 2" round LCD
# TODO: Set up CAN bus (Innomaker USB2CAN, gs_usb/SocketCAN)
# TODO: Set up GPS serial (NEO-6MV2 on UART, 9600 baud)
# TODO: Parse NMEA sentences for lat, lon, speed, time, date, elevation
# TODO: On first fix: set Pi system time from GPS
# TODO: Compute sunrise, sunset, moonrise, moonset, moon phase from lat/lon + date
# TODO: Compute ambient light category from time relative to sunset
# TODO: Broadcast at 2 Hz: speed, time, date, lat, lon, elevation, ambient light
# TODO: Display: 24hr rim, moon phase, time HH:MM, day-of-week
# TODO: Show "Waiting on Fix..." until GPS has a fix


def main():
    print("[GPS] GPS display starting...")
    print(f"[GPS] CAN bus speed: {can_ids.CAN_BUS_SPEED} bps")
    print(f"[GPS] Broadcasting on 0x{can_ids.CAN_ID_GPS_SPEED:03X}–0x{can_ids.CAN_ID_GPS_AMBIENT_LIGHT:03X}")

    # TODO: Initialize display
    # TODO: Initialize GPS serial
    # TODO: Initialize CAN bus
    # TODO: Start heartbeat broadcast
    # TODO: Enter main loop

    print("[GPS] Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
