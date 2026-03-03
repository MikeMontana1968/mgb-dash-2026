"""Generate B&W pinout PNGs for all MGB Dash ESP32 and Raspberry Pi boards.
Laser-printer-friendly: no fills, thin outlines, condensed layout.
"""
from PIL import Image, ImageDraw, ImageFont
from datetime import date
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "C:/Windows/Fonts"
TODAY = date.today().strftime("%Y-%m-%d")

BK = (0, 0, 0)
WH = (255, 255, 255)
GY = (150, 150, 150)
LG = (200, 200, 200)

# ═════════════════════════════════════════════════════════════════
# ESP32 DevKit V1 (30-pin) base layout
# ═════════════════════════════════════════════════════════════════
ESP_LEFT = [
    (1,  "3V3",    None), (2,  "EN",     None),
    (3,  "GPIO36", 36),   (4,  "GPIO39", 39),
    (5,  "GPIO34", 34),   (6,  "GPIO35", 35),
    (7,  "GPIO32", 32),   (8,  "GPIO33", 33),
    (9,  "GPIO25", 25),   (10, "GPIO26", 26),
    (11, "GPIO27", 27),   (12, "GPIO14", 14),
    (13, "GPIO12", 12),   (14, "GND",    None),
    (15, "GPIO13", 13),
]
ESP_RIGHT = [
    (30, "VIN",    None), (29, "GND",    None),
    (28, "GPIO23", 23),   (27, "GPIO22", 22),
    (26, "TX0",    1),    (25, "RX0",    3),
    (24, "GPIO21", 21),   (23, "GND",    None),
    (22, "GPIO19", 19),   (21, "GPIO18", 18),
    (20, "GPIO5",  5),    (19, "GPIO17", 17),
    (18, "GPIO16", 16),   (17, "GPIO4",  4),
    (16, "GPIO2",  2),
]
# ═════════════════════════════════════════════════════════════════
# ideaspark ESP32+OLED 0.96" board (30-pin, pin 1 at bottom near USB)
# SSD1306 OLED hardwired to GPIO21 (SDA) / GPIO22 (SCL)
# ═════════════════════════════════════════════════════════════════
ISPARK_LEFT = [
    (15, "EN",      None),
    (14, "GPIO36",  36),   (13, "GPIO39", 39),
    (12, "GPIO34",  34),   (11, "GPIO35", 35),
    (10, "GPIO32",  32),   (9,  "GPIO33", 33),
    (8,  "GPIO25",  25),   (7,  "GPIO26", 26),
    (6,  "GPIO27",  27),   (5,  "GPIO14", 14),
    (4,  "GPIO12",  12),   (3,  "GPIO13", 13),
    (2,  "GND",     None), (1,  "VIN",    None),
]
ISPARK_RIGHT = [
    (15, "GPIO23",  23),   (14, "GPIO22", 22),
    (13, "TX0",     1),    (12, "RX0",    3),
    (11, "GPIO21",  21),   (10, "GPIO19", 19),
    (9,  "GPIO18",  18),   (8,  "GPIO5",  5),
    (7,  "GPIO17",  17),   (6,  "GPIO16", 16),
    (5,  "GPIO4",   4),    (4,  "GPIO2",  2),
    (3,  "GPIO15",  15),   (2,  "GND",    None),
    (1,  "3V3",     None),
]

ESP_ENVS = {
    "servo_fuel": {
        "title": "Servo Gauge \u2014 FUEL (SOC)",
        "subtitle": "CAN + NeoPixel LED ring + servo",
        "signals": {5: "CAN_TX", 4: "CAN_RX", 14: "LED_DATA", 27: "SERVO"},
    },
    "servo_amps": {
        "title": "Servo Gauge \u2014 AMPS",
        "subtitle": "CAN + NeoPixel LED ring + servo",
        "signals": {5: "CAN_TX", 4: "CAN_RX", 14: "LED_DATA", 27: "SERVO"},
    },
    "servo_temp": {
        "title": "Servo Gauge \u2014 TEMP",
        "subtitle": "CAN + NeoPixel LED ring + servo",
        "signals": {5: "CAN_TX", 4: "CAN_RX", 14: "LED_DATA", 27: "SERVO"},
    },
    "speedometer": {
        "title": "Speedometer",
        "subtitle": "CAN + stepper + servo + LED ring + OLED (I2C, on-board)",
        "board": "ideaspark",
        "signals": {
            32: "CAN_TX", 35: "CAN_RX",
            33: "STEP_IN1", 25: "STEP_IN2", 26: "STEP_IN3", 27: "STEP_IN4",
            34: "STEP_HOME",
            14: "LED_DATA", 13: "SERVO",
            21: "OLED_SDA", 22: "OLED_SCL",
        },
    },
    "body_controller": {
        "title": "Body Controller",
        "subtitle": "CAN 12/25 + hall sensor + 13 resistor-divider inputs (12V)",
        "signals": {
            12: "CAN_TX", 25: "CAN_RX", 35: "HALL",
            23: "KEY_ON", 22: "KEY_START", 21: "KEY_ACC",
            19: "L_TURN", 18: "R_TURN", 17: "HAZARD",
            4: "RUN_LIGHT", 32: "HEADLIGHT", 26: "BRAKE",
            27: "REGEN", 14: "FAN", 16: "REVERSE", 5: "CHARGE",
        },
    },
}

# ═════════════════════════════════════════════════════════════════
# Raspberry Pi 40-pin header layout (BCM numbering)
# ═════════════════════════════════════════════════════════════════
# Odd pins (left column, top to bottom)
PI_LEFT = [
    (1,  "3V3",     None), (3,  "GPIO2",  2),
    (5,  "GPIO3",   3),    (7,  "GPIO4",  4),
    (9,  "GND",     None), (11, "GPIO17", 17),
    (13, "GPIO27",  27),   (15, "GPIO22", 22),
    (17, "3V3",     None), (19, "GPIO10", 10),
    (21, "GPIO9",   9),    (23, "GPIO11", 11),
    (25, "GND",     None), (27, "GPIO0",  0),
    (29, "GPIO5",   5),    (31, "GPIO6",  6),
    (33, "GPIO13",  13),   (35, "GPIO19", 19),
    (37, "GPIO26",  26),   (39, "GND",    None),
]
# Even pins (right column, top to bottom)
PI_RIGHT = [
    (2,  "5V",      None), (4,  "5V",     None),
    (6,  "GND",     None), (8,  "GPIO14", 14),
    (10, "GPIO15",  15),   (12, "GPIO18", 18),
    (14, "GND",     None), (16, "GPIO23", 23),
    (18, "GPIO24",  24),   (20, "GND",    None),
    (22, "GPIO25",  25),   (24, "GPIO8",  8),
    (26, "GPIO7",   7),    (28, "GPIO1",  1),
    (30, "GND",     None), (32, "GPIO12", 12),
    (34, "GND",     None), (36, "GPIO16", 16),
    (38, "GPIO20",  20),   (40, "GPIO21", 21),
]
PI_ENVS = {
    "gps_display": {
        "title": "GPS Display \u2014 Pi 3B",
        "subtitle": "SPI0 LCD (GC9A01 240x240) + UART GPS (NEO-6M) + I2C RTC + USB CAN",
        "signals": {
            2: "I2C_SDA",    3: "I2C_SCL",
            10: "LCD_MOSI",  11: "LCD_SCK",   8: "LCD_CS",
            25: "LCD_DC",    27: "LCD_RST",  18: "LCD_BL/PWM",
            14: "GPS_TXD",   15: "GPS_RXD",
        },
    },
    "primary_display": {
        "title": "Primary Display \u2014 Pi 4B",
        "subtitle": "DSI LCD (ribbon connector) + I2C RTC (PCF8523) + USB CAN",
        "signals": {
            2: "I2C_SDA",  3: "I2C_SCL",
        },
        "notes": ["DSI display via dedicated ribbon connector (not GPIO)"],
    },
}


# ═════════════════════════════════════════════════════════════════
# Shared drawing helpers
# ═════════════════════════════════════════════════════════════════
def _fonts():
    return (
        ImageFont.truetype(f"{FONT_DIR}/consolab.ttf", 20),  # title
        ImageFont.truetype(f"{FONT_DIR}/consola.ttf",  11),  # sub
        ImageFont.truetype(f"{FONT_DIR}/consola.ttf",  14),  # gpio
        ImageFont.truetype(f"{FONT_DIR}/consolab.ttf", 13),  # sig
        ImageFont.truetype(f"{FONT_DIR}/consola.ttf",  10),  # pin
    )


def _draw_header(d, f_title, f_sub, f_pin, title, subtitle, n_used, img_w,
                 board_label, bx1, by1, bx2, by2, usb=False):
    """Title, subtitle, board outline, label."""
    bb = d.textbbox((0, 0), title, font=f_title)
    d.text(((img_w - bb[2]) // 2, 10), title, fill=BK, font=f_title)

    sub = f"{subtitle}  \u2502  {n_used} GPIOs  \u2502  {TODAY}"
    bb = d.textbbox((0, 0), sub, font=f_sub)
    d.text(((img_w - bb[2]) // 2, 36), sub, fill=GY, font=f_sub)

    d.rounded_rectangle([bx1, by1, bx2, by2], radius=5,
                        fill=WH, outline=BK, width=2)

    bb = d.textbbox((0, 0), board_label, font=f_title)
    d.text((img_w // 2 - bb[2] // 2, by1 + (by2 - by1) // 2 - 12),
           board_label, fill=LG, font=f_title)

    # Pin-1 marker
    d.arc([bx1 + (bx2 - bx1) // 2 - 6, by1 - 3,
           bx1 + (bx2 - bx1) // 2 + 6, by1 + 3],
          start=0, end=180, fill=BK, width=1)

    if usb:
        uw, uh = 36, 14
        ux, uy = img_w // 2 - uw // 2, by2 - 2
        d.rounded_rectangle([ux, uy, ux + uw, uy + uh], radius=2,
                            fill=WH, outline=BK, width=1)
        bb = d.textbbox((0, 0), "USB", font=f_pin)
        d.text((img_w // 2 - bb[2] // 2, uy + 1), "USB", fill=GY, font=f_pin)


def _draw_legend(d, f_pin, img_w, y):
    lx = img_w // 2 - 150
    r = 4
    d.ellipse([lx, y, lx + 2*r, y + 2*r], fill=BK)
    d.text((lx + 12, y - 1), "= Project signal", fill=BK, font=f_pin)
    lx += 160
    d.ellipse([lx, y, lx + 2*r, y + 2*r], fill=WH, outline=BK, width=1)
    d.text((lx + 12, y - 1), "= Unused / Power / GND", fill=GY, font=f_pin)


def _draw_pin_left(d, f_gpio, f_sig, f_pin, signals,
                   y, pnum, glabel, gnum, bx1, pin_r):
    used = gnum is not None and gnum in signals
    sig  = signals.get(gnum, "") if gnum else ""

    px = bx1 - 2
    if used:
        d.ellipse([px-pin_r, y-pin_r, px+pin_r, y+pin_r], fill=BK)
    else:
        d.ellipse([px-pin_r, y-pin_r, px+pin_r, y+pin_r],
                  fill=WH, outline=BK, width=1)

    d.line([(px-pin_r-2, y), (bx1-50, y)], fill=LG, width=1)
    d.text((bx1-26, y-6), f"{pnum:>2}", fill=GY, font=f_pin)

    bb = d.textbbox((0, 0), glabel, font=f_gpio)
    gw = bb[2] - bb[0]
    gx = bx1 - 56 - gw
    d.text((gx, y-8), glabel, fill=BK if used else GY, font=f_gpio)

    if sig:
        bb = d.textbbox((0, 0), sig, font=f_sig)
        sw = bb[2] - bb[0]
        sx = gx - sw - 14
        d.rounded_rectangle([sx-3, y-9, sx+sw+3, y+7],
                            radius=2, fill=WH, outline=BK, width=1)
        d.text((sx, y-8), sig, fill=BK, font=f_sig)


def _draw_pin_right(d, f_gpio, f_sig, f_pin, signals,
                    y, pnum, glabel, gnum, bx2, pin_r):
    used = gnum is not None and gnum in signals
    sig  = signals.get(gnum, "") if gnum else ""

    px = bx2 + 2
    if used:
        d.ellipse([px-pin_r, y-pin_r, px+pin_r, y+pin_r], fill=BK)
    else:
        d.ellipse([px-pin_r, y-pin_r, px+pin_r, y+pin_r],
                  fill=WH, outline=BK, width=1)

    d.line([(px+pin_r+2, y), (bx2+50, y)], fill=LG, width=1)
    d.text((bx2+20, y-6), f"{pnum:<2}", fill=GY, font=f_pin)

    gx = bx2 + 56
    d.text((gx, y-8), glabel, fill=BK if used else GY, font=f_gpio)

    if sig:
        bb = d.textbbox((0, 0), glabel, font=f_gpio)
        gw = bb[2] - bb[0]
        sx = gx + gw + 12
        bb = d.textbbox((0, 0), sig, font=f_sig)
        sw = bb[2] - bb[0]
        d.rounded_rectangle([sx-3, y-9, sx+sw+3, y+7],
                            radius=2, fill=WH, outline=BK, width=1)
        d.text((sx, y-8), sig, fill=BK, font=f_sig)


# ═════════════════════════════════════════════════════════════════
# ESP32 generator
# ═════════════════════════════════════════════════════════════════
def generate_esp32(env_name, env_data):
    board = env_data.get("board", "devkit")
    if board == "ideaspark":
        left_pins, right_pins = ISPARK_LEFT, ISPARK_RIGHT
        board_label = "ESP32"
        title = f"MGB {env_data['title']} \u2014 ideaspark ESP32+OLED Pinout"
    else:
        left_pins, right_pins = ESP_LEFT, ESP_RIGHT
        board_label = "ESP32"
        title = f"MGB {env_data['title']} \u2014 ESP32 DevKit Pinout"

    NUM, PIN_SP, BD_W, PIN_R = 15, 38, 120, 4
    BD_TOP = 72
    PIN_Y0 = BD_TOP + 30
    BD_H   = NUM * PIN_SP + 28
    IMG_W  = 1500
    IMG_H  = BD_TOP + BD_H + 46

    bx1 = IMG_W // 2 - BD_W // 2
    bx2 = bx1 + BD_W

    signals   = env_data["signals"]
    off_board = env_data.get("off_board", {})
    n_used    = len(signals) + len(off_board)

    img = Image.new("RGB", (IMG_W, IMG_H), WH)
    d = ImageDraw.Draw(img)
    f_title, f_sub, f_gpio, f_sig, f_pin = _fonts()

    _draw_header(d, f_title, f_sub, f_pin, title, env_data.get("subtitle", ""),
                 n_used, IMG_W, board_label, bx1, BD_TOP, bx2, BD_TOP + BD_H, usb=True)

    for i, (pn, gl, gn) in enumerate(left_pins):
        y = PIN_Y0 + i * PIN_SP
        _draw_pin_left(d, f_gpio, f_sig, f_pin, signals, y, pn, gl, gn, bx1, PIN_R)
    for i, (pn, gl, gn) in enumerate(right_pins):
        y = PIN_Y0 + i * PIN_SP
        _draw_pin_right(d, f_gpio, f_sig, f_pin, signals, y, pn, gl, gn, bx2, PIN_R)

    foot_y = BD_TOP + BD_H + 8
    if off_board:
        parts = [f"GPIO{g}: {s}" for g, s in off_board.items()]
        note = "* Not on 30-pin header: " + ", ".join(parts)
        bb = d.textbbox((0, 0), note, font=f_pin)
        d.text(((IMG_W - bb[2]) // 2, foot_y), note, fill=BK, font=f_pin)
        foot_y += 16
    _draw_legend(d, f_pin, IMG_W, foot_y + 4)

    out = os.path.join(SCRIPT_DIR, f"{env_name}-pinout.png")
    img.save(out, "PNG", dpi=(300, 300))
    print(f"  {out}")


# ═════════════════════════════════════════════════════════════════
# Raspberry Pi generator
# ═════════════════════════════════════════════════════════════════
def generate_pi(env_name, env_data):
    NUM, PIN_SP, BD_W, PIN_R = 20, 34, 80, 4
    BD_TOP = 72
    PIN_Y0 = BD_TOP + 26
    BD_H   = NUM * PIN_SP + 20
    IMG_W  = 1500
    IMG_H  = BD_TOP + BD_H + 60

    bx1 = IMG_W // 2 - BD_W // 2
    bx2 = bx1 + BD_W

    signals = env_data["signals"]
    notes   = env_data.get("notes", [])
    n_used  = len(signals)

    img = Image.new("RGB", (IMG_W, IMG_H), WH)
    d = ImageDraw.Draw(img)
    f_title, f_sub, f_gpio, f_sig, f_pin = _fonts()

    title = f"MGB {env_data['title']} \u2014 40-Pin Header Pinout"
    _draw_header(d, f_title, f_sub, f_pin, title, env_data.get("subtitle", ""),
                 n_used, IMG_W, "Pi", bx1, BD_TOP, bx2, BD_TOP + BD_H, usb=False)

    for i, (pn, gl, gn) in enumerate(PI_LEFT):
        y = PIN_Y0 + i * PIN_SP
        _draw_pin_left(d, f_gpio, f_sig, f_pin, signals, y, pn, gl, gn, bx1, PIN_R)
    for i, (pn, gl, gn) in enumerate(PI_RIGHT):
        y = PIN_Y0 + i * PIN_SP
        _draw_pin_right(d, f_gpio, f_sig, f_pin, signals, y, pn, gl, gn, bx2, PIN_R)

    foot_y = BD_TOP + BD_H + 8
    if notes:
        for note in notes:
            bb = d.textbbox((0, 0), note, font=f_pin)
            d.text(((IMG_W - bb[2]) // 2, foot_y), note, fill=BK, font=f_pin)
            foot_y += 14
    _draw_legend(d, f_pin, IMG_W, foot_y + 4)

    out = os.path.join(SCRIPT_DIR, f"{env_name}-pinout.png")
    img.save(out, "PNG", dpi=(300, 300))
    print(f"  {out}")


# ═════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    for name, data in ESP_ENVS.items():
        generate_esp32(name, data)
    for name, data in PI_ENVS.items():
        generate_pi(name, data)
    print("Done.")
