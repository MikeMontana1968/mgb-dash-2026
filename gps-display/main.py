"""
MGB Dash 2026 — GPS Display (Pi 3B)

Waveshare 1.28" round GC9A01 LCD (240x240, RGB565) with NEO-6M GPS receiver.
Broadcasts GPS data on CAN, displays 24hr clock with moon phase.

Hardware GPIO (BCM numbering):
  LCD SPI0:  MOSI=10, SCK=11, CS=8 (standard SPI0 pins)
  LCD ctrl:  DC=25, RST=27, BL=18 (PWM backlight at 1kHz)
  GPS UART:  TXD0=14, RXD0=15 (9600 baud -> gpsd daemon)
  CAN:       Innomaker USB2CAN (gs_usb driver, SocketCAN can0)

GPS access is via gpsd daemon (TCP localhost:2947), not direct serial.
See pi-setup/gps-display.sh for UART->gpsd and SPI setup.
"""

import sys
import os
import signal
import struct
import time
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.python import can_ids
from common.python.can_log import can_log, LogRole, LogLevel, LogEvent
from common.python.log_setup import setup_logging

logger = setup_logging("gps")

import gpsd
import can
from tendo import singleton

import ephemeris
from presenter import Presenter


# ── Signal Handler ────────────────────────────────────────────────────
class SignalHandler:
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def continue_looping(self):
        return not self.shutdown_requested

    def handle_signal(self, signum, frame):
        logger.info(f"Received signal {signum}. Exiting gracefully...")
        self.shutdown_requested = True


# ── GPSD Connection ───────────────────────────────────────────────────
def WaitForGPSD(presenter, sig):
    """Two-phase startup: connect to gpsd, then wait for satellite fix.

    Phase 1: Connect to gpsd daemon (retry every 5s, display updates every 1s)
    Phase 2: Poll for fix.mode >= 2 (satellite fix, poll every 1s)
    Returns True when fix acquired, False if shutdown requested.
    """
    start = time.monotonic()

    while sig.continue_looping():
        # Phase 1 — connect to gpsd daemon
        elapsed = int(time.monotonic() - start)
        presenter.write_waiting(elapsed)
        logger.info("gpsd.connecting...")
        try:
            gpsd.connect()
        except Exception as e:
            logger.error(f"gpsd connection failed: {e}")
            # Wait 5s but update display every 1s and check for shutdown
            for _ in range(5):
                if not sig.continue_looping():
                    return False
                time.sleep(1)
                elapsed = int(time.monotonic() - start)
                presenter.write_waiting(elapsed)
            continue

        # Phase 2 — wait for satellite fix
        logger.info("gpsd connected, waiting for satellite fix...")
        while sig.continue_looping():
            elapsed = int(time.monotonic() - start)
            presenter.write_waiting(elapsed)
            try:
                fix = gpsd.get_current()
                if fix.mode >= 2:
                    logger.info(f"Satellite fix acquired (mode={fix.mode}) after {elapsed}s")
                    return True
                logger.info(f"No fix yet (mode={fix.mode}), waiting...")
            except Exception as e:
                logger.error(f"gpsd lost during fix wait: {e}")
                break  # back to Phase 1
            time.sleep(1)

    return False


# ── CAN Broadcasting ─────────────────────────────────────────────────
def broadcast_can(bus, fix, gps_time, lat, lon, alt):
    """Broadcast GPS data as CAN messages using monorepo IDs."""
    try:
        # GPS_SPEED (0x720) — mph as 64-bit double
        mph = fix.speed() * 2.23694  # m/s -> mph
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_SPEED,
            is_extended_id=False,
            data=bytearray(struct.pack("d", mph)),
        ))

        # GPS_TIME (0x721) — seconds since midnight UTC as 64-bit double
        secs = gps_time.hour * 3600 + gps_time.minute * 60 + gps_time.second
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_TIME,
            is_extended_id=False,
            data=bytearray(struct.pack("d", float(secs))),
        ))

        # GPS_DATE (0x722) — days since 2000-01-01 as 64-bit double
        epoch = date(2000, 1, 1)
        days = (gps_time.date() - epoch).days
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_DATE,
            is_extended_id=False,
            data=bytearray(struct.pack("d", float(days))),
        ))

        # GPS_LATITUDE (0x723) — decimal degrees as 64-bit double
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_LATITUDE,
            is_extended_id=False,
            data=bytearray(struct.pack("d", lat)),
        ))

        # GPS_LONGITUDE (0x724) — decimal degrees as 64-bit double
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_LONGITUDE,
            is_extended_id=False,
            data=bytearray(struct.pack("d", lon)),
        ))

        # GPS_ELEVATION (0x725) — meters ASL as 64-bit double
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_ELEVATION,
            is_extended_id=False,
            data=bytearray(struct.pack("d", alt)),
        ))

        # GPS_AMBIENT_LIGHT (0x726) — category byte 0-3
        ambient = compute_ambient_light(gps_time, lat, lon)
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_GPS_AMBIENT_LIGHT,
            is_extended_id=False,
            data=bytearray([ambient]),
        ))

    except Exception as e:
        logger.error(f"CAN broadcast error: {e}")


# ── Ambient Light ─────────────────────────────────────────────────────
def compute_ambient_light(gps_time, lat, lon):
    """Compute ambient light category from sun position.

    Returns:
        0 = DAYLIGHT, 1 = EARLY_TWILIGHT, 2 = LATE_TWILIGHT, 3 = DARKNESS
    """
    try:
        sun = ephemeris.getSunDates(gps_time, lat, lon)
        now = gps_time

        if sun['rise'] <= now <= sun['set']:
            return can_ids.AMBIENT_DAYLIGHT
        elif sun['dawn'] <= now <= sun['dusk']:
            return can_ids.AMBIENT_EARLY_TWILIGHT
        elif sun['nauticalDawn'] <= now <= sun['nauticalDusk']:
            return can_ids.AMBIENT_LATE_TWILIGHT
        else:
            return can_ids.AMBIENT_DARKNESS
    except Exception as e:
        logger.error(f"Ambient light calc failed: {e}")
        return can_ids.AMBIENT_DARKNESS


# ── Heartbeat ─────────────────────────────────────────────────────────
def send_heartbeat(bus, counter):
    """Send heartbeat CAN message: role 'GPS  ' + rolling counter."""
    try:
        payload = bytearray(can_ids.HEARTBEAT_LEN)
        payload[0:5] = can_ids.ROLE_GPS
        payload[5] = counter & 0xFF
        payload[6] = 0x00  # error flags
        payload[7] = 0x00  # reserved
        bus.send(can.Message(
            arbitration_id=can_ids.CAN_ID_HEARTBEAT,
            is_extended_id=False,
            data=payload,
        ))
    except Exception as e:
        logger.error(f"Heartbeat send error: {e}")


# ── Main ──────────────────────────────────────────────────────────────
def main():
    logger.critical("GPS display starting...")

    # Singleton check — prevent duplicate processes
    me = singleton.SingleInstance()

    sig = SignalHandler()

    # Initialize display
    presenter = Presenter(logger)

    # Connect to gpsd and wait for satellite fix
    if not WaitForGPSD(presenter, sig):
        return  # shutdown during startup
    logger.info("GPS Connected")
    presenter.write("Ready!", "GREEN")

    # Initialize CAN bus (non-fatal if unavailable)
    can_bus = None
    try:
        can_bus = can.Bus(channel='can0', interface='socketcan')
        logger.info("CAN bus initialized on can0")
    except Exception as e:
        logger.error(f"CAN bus init failed (continuing without CAN): {e}")

    heartbeat_counter = 0
    has_fix = True  # just came out of WaitForGPSD with a valid fix

    can_log(can_bus, LogRole.GPS, LogLevel.LOG_INFO, LogEvent.GPS_FIX_ACQUIRED)

    # Main loop — 1 Hz
    while sig.continue_looping():
        try:
            fix = gpsd.get_current()
            if fix.mode >= 2:
                if not has_fix:
                    has_fix = True
                    logger.info(f"GPS fix restored (mode={fix.mode})")
                    can_log(can_bus, LogRole.GPS, LogLevel.LOG_INFO, LogEvent.GPS_FIX_ACQUIRED)

                # Normal operation — valid satellite fix
                local_time = fix.get_time(local_time=True)
                speed_mps = fix.speed()
                lat = fix.lat
                lon = fix.lon
                alt = fix.alt

                # Update display
                presenter.use_data(local_time, speed_mps, lat, lon, alt)

                # Broadcast CAN messages
                if can_bus is not None:
                    broadcast_can(can_bus, fix, local_time, lat, lon, alt)
                    send_heartbeat(can_bus, heartbeat_counter)
                    heartbeat_counter += 1
            else:
                if has_fix:
                    has_fix = False
                    logger.warning(f"GPS signal lost (mode={fix.mode})")
                    can_log(can_bus, LogRole.GPS, LogLevel.LOG_WARN, LogEvent.GPS_FIX_LOST)

                # No satellite fix — show system clock + signal lost
                presenter.write_signal_lost(datetime.now().strftime("%-I:%M"))
        except Exception as e:
            if has_fix:
                has_fix = False
                can_log(can_bus, LogRole.GPS, LogLevel.LOG_WARN, LogEvent.GPS_FIX_LOST)

            # Daemon crash — show system clock + signal lost, try reconnect
            logger.error(f"gpsd error: {e}")
            presenter.write_signal_lost(datetime.now().strftime("%-I:%M"))
            try:
                gpsd.connect()
                logger.info("gpsd reconnected")
            except Exception:
                pass

        time.sleep(1)

    # Graceful shutdown
    logger.info("Shutting down...")
    if can_bus is not None:
        can_bus.shutdown()
    logger.info("GPS display stopped.")


if __name__ == "__main__":
    main()
