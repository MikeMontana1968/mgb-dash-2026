# Speedometer

Stepper-motor slot-machine speed display with servo gear indicator, OLED odometer, and 12-LED SK6812 RGBW ring. ESP32 with integrated SSD1306 OLED (128x64, I2C) + TJA1050 CAN transceiver. Receives speed, gear, and odometer from the body controller over CAN.

## Components

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ideaspark ESP32 + integrated 0.96" OLED (CH340) | — | — | SSD1306 128x64 hardwired to I2C |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO32**, RX→**GPIO35** | 5V logic, needs 5V supply |
| LED Ring | SK6812 RGBW, 12 LEDs | Data | **GPIO14** | Adafruit NeoPixel (NEO_GRBW) |
| Gear Indicator Servo | SG90 or MG90S, 180° | PWM | **GPIO13** | Rotates disc to show 1/2/3/4/R/N |
| Stepper Motor | 28BYJ-48 + ULN2003 | GPIO | IN1→**GPIO33**, IN2→**GPIO25**, IN3→**GPIO26**, IN4→**GPIO27** | Drives slot-machine speed drum |
| Home Sensor | Slotted opto-interrupter | Digital In | **GPIO34** | Active-HIGH when marker detected, input-only pin |
| OLED Display | SSD1306 128x64 (on-board) | I2C | SDA→**GPIO21**, SCL→**GPIO22** | Hardwired on ideaspark board, 0x3C, no dedicated RST |
| Voltage Regulator | LM2596 or similar | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | End-of-bus nodes only |

## CAN Messages

| Direction | CAN ID | Name | Rate |
|-----------|--------|------|------|
| Consumes | `0x710` | BODY_STATE | 10 Hz |
| Consumes | `0x711` | BODY_SPEED | 10 Hz |
| Consumes | `0x712` | BODY_GEAR | 2 Hz |
| Consumes | `0x713` | BODY_ODOMETER | 1 Hz |
| Consumes | `0x720` | GPS_SPEED | 2 Hz |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | 2 Hz |
| Consumes | `0x730` | SELF_TEST | On-demand |
| Broadcasts | `0x700` | HEARTBEAT | 1 Hz |

See [common/README.md](../../../common/README.md) for full payload details.

## Behavior

- **Stepper motor** drives a 1:1 wheel with MPH values — slot-machine style display. Uses `StepperWheel` library (28BYJ-48 via ULN2003) with optical home calibration, cubic-eased 1200 ms transitions, and shortest-path rotation.
- **Servo** rotates a gear indicator disc showing "1", "2", "3", "4", "R", "N" through a viewport. Gear angle lookup: Neutral=15°, 1st=30°, 2nd=45°, 3rd=60°, 4th=75°, Reverse=0°.
- **OLED display** (128x64, I2C, SSD1306 integrated on ESP32 board) shows odometer reading in miles. Renders only on value change to minimize I2C traffic.
- **Speed discrepancy indicator**: visual alert when `0x711` (hall sensor speed) and `0x720` (GPS speed) differ by a configurable percentage.
- **LED ring**: turn signal / hazard animation from `0x710`, ambient brightness from `0x726`.
- **Self-test** (`0x730`): needle sweep + LED ring pattern.

## Build

```powershell
cd esp32
pio run -e speedometer
pio run -e speedometer -t upload   # Flash via USB
```

## Pinout

[Speedometer pinout](../../../docs/speedometer-pinout.png)
