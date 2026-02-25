"""
MGB Dash 2026 — GPS Display Presenter

Renders the 24-hour clock dial with sun/moon arcs, time, date, speed,
and moon phase on the Waveshare 1.28" GC9A01 LCD (240x240).

Drawing order (each frame at ~1 Hz):
  1. Speed — top area, tiny font, gray, "{mph} mph"
  2. Moon arc — outer rim, gray, 20px wide, moonrise->moonset span
  3. Sun arc — outer rim, golden (205,205,99), 10px wide, sunrise->sunset span
  4. Hour ticks — 4 cardinal marks at 0h, 6h, 12h, 24h
  5. Moon phase icon — bottom-right, Unicode glyph from moon_phases.ttf
  6. Current time tick — blinking ray at current hour position (1 Hz white/black alternation)
  7. Date — "Sun 23 Feb", medium font, gray, Y=165
  8. Time — "1:30", large 80pt font, white, centered
"""

import math
import os
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from astral import moon

import ephemeris
from lib.LCD_1inch28 import LCD_1inch28


class Presenter:
    CX = 120
    CY = 120
    Center = (CX, CY)
    RotationOffsetDegrees = 90
    ArcBoundBox = (1, 1, 239, 239)
    latitude = 0
    longitude = 0
    gps_time = ""

    def __init__(self, logger):
        self.logger = logger
        self.disp = LCD_1inch28()
        self.disp.Init()
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        self.fontMoonPhases = ImageFont.truetype(f"{font_dir}/moon_phases.ttf", 25)
        self.fontMed        = ImageFont.truetype(f"{font_dir}/ArgentumSans-Light.ttf", 30)
        self.fontLarge      = ImageFont.truetype(f"{font_dir}/ArgentumSans-ExtraBold.ttf", 80)
        self.fontTiny       = ImageFont.truetype(f"{font_dir}/ArgentumSans-Light.ttf", 20)
        self.newCanvas()
        self.counter = 0
        self.last_reported = 0
        self.write("PM!", "GREEN")
        self.logger.info("Presenter initialized")

    def __del__(self):
        self.write("XXX")
        self.logger.critical("-Presenter destructor-")

    def centerText(self, message, theFont, color="WHITE", offsetY=0):
        _, _, w, h = self.canvas.textbbox((0, 0), message, font=theFont)
        box = ((240 - w) / 2, ((240 - h) / 2) + offsetY)
        self.canvas.text(box, message, font=theFont, fill=color)

    def centerTextHorizontal(self, message, theFont, color="WHITE", absoluteY=0):
        _, _, w, h = self.canvas.textbbox((0, 0), message, font=theFont)
        box = ((240 - w) / 2, absoluteY)
        self.canvas.text(box, message, font=theFont, fill=color)

    def SinCos(self, radius, angle):
        return self.CX + (radius * math.sin(angle)), self.CY + (radius * math.cos(angle))

    def drawHourTicks(self, color=(100, 100, 100)):
        for h in [-6, 12, 6, 24]:
            angle = math.radians((h * (360 / 24)))
            self.canvas.line([self.SinCos(120, angle), self.SinCos(100, angle)], color, width=3)

    def drawCurrentTimeTick(self):
        h = ephemeris.timeToDecimalHours(self.gps_time)
        angle = math.radians((-h * (360 / 24)))
        if int(time.monotonic()) % 2:
            majorColor = "WHITE"
            minorColor = "BLACK"
        else:
            majorColor = "BLACK"
            minorColor = "WHITE"

        self.canvas.line([self.SinCos(120, angle), self.SinCos(100, angle)], majorColor, width=10)
        self.canvas.line([self.SinCos(120, angle), self.SinCos(100, angle)], minorColor, width=3)

    def drawRay24Hour(self, hours, color):
        radius = 150
        angle = math.radians(self.RotationOffsetDegrees + (hours * (360 / 24)))
        dy = 120 + (radius * math.sin(angle))
        dx = 120 + (radius * math.cos(angle))
        self.canvas.line([self.Center, (dx, dy)], color, width=10)

    def drawMoonArc(self, color=(80, 80, 80)):
        moon_times = ephemeris.getMoonTimes(self.gps_time, self.latitude, self.longitude)
        rise = 0
        set_time = 24
        if 'rise' in moon_times:
            rise = ephemeris.timeToDecimalHours(moon_times['rise'])
        if 'set' in moon_times:
            set_time = ephemeris.timeToDecimalHours(moon_times['set'])

        self.canvas.arc(self.ArcBoundBox, 90 + (15 * rise), 90 + (15 * set_time), fill=color, width=20)

    def drawSunArc(self, color=(205, 205, 99)):
        sun = ephemeris.getSunDates(self.gps_time, self.latitude, self.longitude)
        sunrise = ephemeris.timeToDecimalHours(sun['rise'])
        sunset = ephemeris.timeToDecimalHours(sun['set'])
        self.canvas.arc(
            self.ArcBoundBox,
            self.RotationOffsetDegrees + (15 * sunrise),
            self.RotationOffsetDegrees + (15 * sunset),
            fill=color, width=10,
        )

    def drawSunMoonIcons(self):
        phase = moon.phase(self.gps_time)
        c = int(64 + phase)
        self.canvas.text((100, 210), chr(c), fill="WHITE", font=self.fontMoonPhases)

    def mps_to_mph(self, mps):
        return 2.23694 * mps

    def displaySpeed(self, yPosition=37):
        msg = f"{round(self.mps_to_mph(self.speedMetersSecond))} mph"
        self.centerTextHorizontal(msg, self.fontTiny, (150, 150, 150), absoluteY=yPosition)

    def displayDate(self, AbsY=37, color=(128, 128, 128)):
        self.centerTextHorizontal(
            self.gps_time.strftime("%a %-d %b"), self.fontMed, color, absoluteY=AbsY,
        )

    def displayTime(self, yPosition=63, color="WHITE"):
        self.centerText(self.gps_time.strftime("%-I:%M"), self.fontLarge, color, yPosition)

    def write(self, message="GPS?", color="RED"):
        self.newCanvas()
        if len(message) > 15:
            self.centerText(message, self.fontTiny, color)
        else:
            self.centerText(message, self.fontMed, color)
        self.disp.ShowImage(self.CompostingImage)

    def write_waiting(self, elapsed_secs):
        """Startup screen: 'Waiting for GPS' with elapsed seconds counter."""
        self.newCanvas()
        self.centerText("Waiting for GPS", self.fontMed, "RED", offsetY=-25)
        self.centerText(str(elapsed_secs), self.fontLarge, "RED", offsetY=25)
        self.disp.ShowImage(self.CompostingImage)

    def write_signal_lost(self, local_time_str):
        """Signal-lost fallback: system clock time + 'signal lost' label."""
        self.newCanvas()
        self.centerText(local_time_str, self.fontLarge, "WHITE", offsetY=-20)
        self.centerText("signal lost", self.fontMed, "RED", offsetY=30)
        self.disp.ShowImage(self.CompostingImage)

    def newCanvas(self):
        self.CompostingImage = Image.new("RGB", (self.disp.width, self.disp.height), "BLACK")
        self.canvas = ImageDraw.Draw(self.CompostingImage)
        return self.canvas

    def use_data(self, local_time: datetime, speedMps: float, lat: float, lng: float, alt: float):
        self.counter += 1
        t = local_time.strftime("%H:%M:%S")
        self.logger.info(f"use_data({t}, Pos({lat:.3f} {lng:.3f}), {speedMps=}ms, {alt=:.1f}m)")
        self.gps_time = local_time
        self.speedMetersSecond = speedMps
        self.latitude = lat
        self.longitude = lng
        self.altitude = alt

        self.update_display()

    def update_display(self):
        try:
            self.newCanvas()
            self.displaySpeed()
            self.drawMoonArc()
            self.drawSunArc()
            self.drawHourTicks()
            self.drawSunMoonIcons()
            self.drawCurrentTimeTick()
            self.displayDate(165)  # absolute Y
            self.displayTime(-20)  # Y is relative to center of display
        except Exception as eMsg:
            self.logger.error(f"disp refresh failed {eMsg}")
            self.write(str(eMsg))
        finally:
            self.disp.ShowImage(self.CompostingImage)
