# Speedometer

Stepper-motor slot-machine speed display with servo gear indicator, eInk odometer, and 12-LED WS2812B ring. ESP32 + TJA1050 CAN transceiver. Receives speed, gear, and odometer from the body controller over CAN.

## Components

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO5**, RX→**GPIO4** | 5V logic, needs 5V supply |
| LED Ring | WS2812B, 12 LEDs | Data | **GPIO14** | Adafruit NeoPixel |
| Gear Indicator Servo | SG90 or MG90S, 180° | PWM | **GPIO27** | Rotates disc to show 1/2/3/4/R/N |
| Stepper Motor | 28BYJ-48 + ULN2003 | GPIO | IN1→**GPIO25**, IN2→**GPIO26**, IN3→**GPIO32**, IN4→**GPIO33** | Drives slot-machine speed drum |
| Home Sensor | Slotted opto-interrupter | Digital In | **GPIO13** | Active-HIGH when marker detected |
| eInk Display | Waveshare 1.54" tri-color | SPI | MOSI→**GPIO23**, SCK→**GPIO18**, CS→**GPIO15**, DC→**GPIO17**, RST→**GPIO16**, BUSY→**GPIO2** | 200x200, black/white/red, 3.3V |
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
- **eInk display** (200x200, SPI, tri-color) shows odometer reading. *(Driver not yet implemented.)*
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
