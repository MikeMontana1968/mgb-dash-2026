"""
MGB Dash 2026 — GPS Display (Pi 3B)

Waveshare 1.28" round GC9A01 LCD (240x240, RGB565) with NEO-6M GPS receiver.
Broadcasts GPS data on CAN, displays 24hr clock with moon phase.

Hardware GPIO (BCM numbering):
  LCD SPI0:  MOSI=10, SCK=11, CS=8 (standard SPI0 pins)
  LCD ctrl:  DC=25, RST=27, BL=18 (PWM backlight at 1kHz)
  GPS UART:  TXD0=14, RXD0=15 (9600 baud → gpsd daemon)
  CAN:       Innomaker USB2CAN (gs_usb driver, SocketCAN can0)

GPS access is via gpsd daemon (TCP localhost:2947), not direct serial.
See pi-setup/gps-display.sh for UART→gpsd and SPI setup.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.python import can_ids
from common.python.log_setup import setup_logging

logger = setup_logging("gps")

# TODO: Import python-can — import can; bus = can.interface.Bus(channel='can0', interface='socketcan')
# TODO: Import gpsd-py3 — import gpsd; gpsd.connect() (talks to gpsd daemon on localhost:2947)
# TODO: Import ephem or astral (for sunrise/sunset/moon calculations)
# TODO: Import display driver — from lib.LCD_1inch28 import LCD_1inch28
# TODO: Import Pillow — from PIL import Image, ImageDraw, ImageFont
# TODO: Set up CAN bus (Innomaker USB2CAN, gs_usb/SocketCAN)
# TODO: Initialize LCD — disp = LCD_1inch28(); disp.Init(); disp.clear()
# TODO: Connect to gpsd — gpsd.connect(); fix = gpsd.get_current()
# TODO: On first fix: set Pi system time from GPS (see pi-setup/gps-display.sh)
# TODO: Compute sunrise, sunset, moonrise, moonset, moon phase from lat/lon + date
# TODO: Compute ambient light category from time relative to sunset
# TODO: Broadcast at 2 Hz: speed, time, date, lat, lon, elevation, ambient light
# TODO: Display: 24hr rim, moon phase, time HH:MM, day-of-week
# TODO: Show "Waiting on Fix..." until GPS has a fix


def main():
    logger.critical("GPS display starting...")
    logger.info("CAN bus speed: %d bps", can_ids.CAN_BUS_SPEED)
    logger.info(
        "Broadcasting on 0x%03X–0x%03X",
        can_ids.CAN_ID_GPS_SPEED,
        can_ids.CAN_ID_GPS_AMBIENT_LIGHT,
    )

    # TODO: Initialize display
    # TODO: Connect to gpsd daemon
    # TODO: Initialize CAN bus
    # TODO: Start heartbeat broadcast
    # TODO: Enter main loop

    logger.info("Not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
