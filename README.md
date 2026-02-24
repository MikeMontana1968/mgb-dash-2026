# MGB Dash 2026

CAN bus dashboard controller for a Nissan Leaf EV conversion in an MGB body.

Seven modules communicate over a single shared CAN bus: three servo gauges (fuel/amps/temp), a speedometer, a body controller, a primary display, and a GPS display. A phone app connects over BLE, and a test Pi provides CLI diagnostic tools.

## Architecture

```
                            ┌─────────────────────────────┐
                            │      Leaf EV-CAN Bus        │
                            │   500 kbps · 11-bit IDs     │
                            └──────────┬──────────────────┘
                                       │
           ┌──────────┬──────────┬─────┴─────┬──────────┬──────────┬──────────┐
           │          │          │           │          │          │          │
      ┌────┴────┐┌────┴────┐┌───┴───┐┌─────┴─────┐┌───┴───┐┌────┴────┐┌────┴────┐
      │  FUEL   ││  AMPS   ││ TEMP  ││   SPEED   ││ BODY  ││  DASH   ││  GPS    │
      │ Servo   ││ Servo   ││ Servo ││Speedometer││ Ctrl  ││Primary  ││Display  │
      │ Gauge   ││ Gauge   ││ Gauge ││           ││       ││Display  ││         │
      │         ││         ││       ││           ││       ││         ││         │
      │ ESP32   ││ ESP32   ││ ESP32 ││  ESP32    ││ ESP32 ││  Pi 4B  ││ Pi 3B   │
      │ TJA1050 ││ TJA1050 ││TJA1050││ TJA1050  ││TJA1050││USB2CAN  ││USB2CAN  │
      │ Servo   ││ Servo   ││ Servo ││ Stepper   ││ GPIO  ││3.4" DSI ││ 2" LCD  │
      │ 24 LEDs ││ 24 LEDs ││24 LEDs││ eInk      ││ Hall  ││         ││ NEO-6M  │
      │         ││         ││       ││ Servo     ││ BLE   ││         ││         │
      └─────────┘└─────────┘└───────┘│ LEDs      │└───┬───┘└─────────┘└─────────┘
                                     └───────────┘    │
                                                      │ BLE
                                                 ┌────┴────┐
                                                 │  Phone  │
                                                 │  App    │
                                                 │  (PWA)  │
                                                 └─────────┘
```

All ESP32 modules use TWAI (built-in CAN controller) with a TJA1050 external transceiver. Both Raspberry Pis use Innomaker USB2CAN adapters (gs_usb/SocketCAN). The Leaf drivetrain is 2013 (AZE0), the battery is 2014 (also AZE0) — same CAN protocol.

### Bus Topology

Single shared bus. All devices sit directly on the Leaf EV-CAN. Custom dashboard messages coexist with Leaf-native traffic. Estimated bus load is ~28%. Custom CAN IDs occupy the 0x700–0x73F range, which is above all Leaf EV-CAN IDs (~0x5C0) and below OBD-II (0x7DF).

### Safety Mitigations

- **TX ID range guard** — ESP32 firmware blocks transmit of any CAN ID outside 0x700–0x73F, preventing accidental corruption of Leaf bus traffic
- **Bus-off recovery** — Automatic detection and recovery with backoff
- **Heartbeat monitoring** — Primary display tracks all module heartbeats, alerts on timeout
- **Hazard detection** — Body controller state machine detects simultaneous left+right turn signals and broadcasts HAZARD flag instead of individual signals

---

## Modules

### Fuel Gauge (Servo) — `esp32/` env: `servo_fuel`

**Role:** Displays battery state of charge (SOC) on a 180-degree servo needle with a 24-LED WS2812B ring.

**Components:**

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO5**, RX→**GPIO4** | 5V logic, needs 5V supply |
| Servo Motor | SG90 or MG90S, 180° | PWM | **GPIO27** | LEDC channel |
| LED Ring | WS2812B, 12 LEDs | Data | **GPIO14** | Adafruit NeoPixel |
| Voltage Regulator | LM2596 or similar | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | End-of-bus nodes only |

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Consumes | `0x1DB` | LEAF_BATTERY_STATUS | Leaf → | — |
| Consumes | `0x55B` | LEAF_SOC_PRECISE | Leaf → | — |
| Consumes | `0x710` | BODY_STATE | Body → | 10 Hz |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | GPS → | 2 Hz |
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |

**Behavior:**
- Servo: 0–180° sweep maps to 0–100% SOC. Primary source: precise SOC from `0x55B`; falls back to coarse SOC from `0x1DB` if precise is stale (>1 s). Smoothing τ=0.8 s.
- LED ring warnings: red (<10% SOC — critically low), amber (<20% — low), ambient otherwise. Amber if CAN data stale >2 s.
- Turn signal / hazard animation overlays from `0x710` body flags, with 600 ms holdoff to bridge relay blink gaps. Priority: hazard > left > right.
- Ambient white backlight level driven by `0x726` (DAYLIGHT=dim, DARKNESS=bright).
- CAN silence watchdog: blue breathing pulse if no CAN traffic within 5 s of boot.

---

### Amps Gauge (Servo) — `esp32/` env: `servo_amps`

**Role:** Displays battery pack current (discharge/regen) as a center-zero gauge.

**Components:**

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO5**, RX→**GPIO4** | 5V logic, needs 5V supply |
| Servo Motor | SG90 or MG90S, 180° | PWM | **GPIO27** | LEDC channel |
| LED Ring | WS2812B, 12 LEDs | Data | **GPIO14** | Adafruit NeoPixel |
| Voltage Regulator | LM2596 or similar | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | End-of-bus nodes only |

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Consumes | `0x1DB` | LEAF_BATTERY_STATUS | Leaf → | — |
| Consumes | `0x710` | BODY_STATE | Body → | 10 Hz |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | GPS → | 2 Hz |
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |

**Behavior:**
- Servo: 0–180° sweep maps -100 A (regen) to +200 A (discharge). Smoothing τ=0.3 s (snappy — current changes fast).
- Current sourced from `0x1DB` bytes 2–3 (upper 11 bits, signed, factor 0.5). Positive = discharge, negative = regen.
- LED ring warnings: red (>150 A absolute — extreme current), amber (>100 A absolute — high current), ambient otherwise. Amber if CAN data stale >2 s.
- Turn signal / hazard animation overlays from `0x710` body flags, with 600 ms holdoff. Priority: hazard > left > right.
- Ambient white backlight level driven by `0x726`. CAN silence watchdog: blue breathing pulse.

---

### Temp Gauge (Servo) — `esp32/` env: `servo_temp`

**Role:** Displays the highest of three inverter/motor temperatures converted to Fahrenheit.

**Components:**

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO5**, RX→**GPIO4** | 5V logic, needs 5V supply |
| Servo Motor | SG90 or MG90S, 180° | PWM | **GPIO27** | LEDC channel |
| LED Ring | WS2812B, 12 LEDs | Data | **GPIO14** | Adafruit NeoPixel |
| Voltage Regulator | LM2596 or similar | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | End-of-bus nodes only |

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Consumes | `0x5C0` | LEAF_BATTERY_TEMP | Leaf → | — |
| Consumes | `0x710` | BODY_STATE | Body → | 10 Hz |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | GPS → | 2 Hz |
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |

**Behavior:**
- Source: `0x5C0` battery temperature (byte 0, signed, offset -40 = °C).
- Servo: 0–180° sweep maps -10 °C to 50 °C. Smoothing τ=1.0 s (slow — temp changes very gradually).
- LED ring warnings: red (>45 °C or <-5 °C — extreme), amber (>35 °C or <0 °C — concerning), ambient otherwise. Amber if CAN data stale >2 s.
- Turn signal / hazard animation overlays from `0x710` body flags, with 600 ms holdoff. Priority: hazard > left > right.
- Ambient white backlight level driven by `0x726`. CAN silence watchdog: blue breathing pulse.

---

### Speedometer — `esp32/` env: `speedometer`

**Role:** Stepper-motor slot-machine speed display, servo gear indicator, eInk odometer, LED ring.

**Components:**

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO5**, RX→**GPIO4** | 5V logic, needs 5V supply |
| LED Ring | WS2812B, 12 LEDs | Data | **GPIO14** | Adafruit NeoPixel |
| Gear Indicator Servo | SG90 or MG90S, 180° | PWM | **GPIO27** | Rotates disc to show 1/2/3/4/R/N |
| Stepper Motor | 28BYJ-48 + ULN2003 | GPIO | STEP→**GPIO25**, DIR→**GPIO26**, EN→**GPIO27** | Drives slot-machine speed drum |
| eInk Display | Waveshare 1.54" tri-color | SPI | MOSI→**GPIO23**, SCK→**GPIO18**, CS→**GPIO5**, DC→**GPIO17**, RST→**GPIO16**, BUSY→**GPIO4** | 200x200, black/white/red, 3.3V |
| Voltage Regulator | LM2596 or similar | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | End-of-bus nodes only |

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Consumes | `0x711` | BODY_SPEED | Body → | 10 Hz |
| Consumes | `0x712` | BODY_GEAR | Body → | 2 Hz |
| Consumes | `0x713` | BODY_ODOMETER | Body → | 1 Hz |
| Consumes | `0x720` | GPS_SPEED | GPS → | 2 Hz |
| Consumes | `0x710` | BODY_STATE | Body → | 10 Hz |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | GPS → | 2 Hz |
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |

**Behavior:**
- Stepper motor drives a 1:1 wheel with MPH values — slot-machine style display.
- Servo rotates a gear indicator disc showing "1", "2", "3", "4", "R", "N" through a viewport.
- Tri-color 1.54" eInk display (200x200, SPI) shows odometer reading.
- Speed discrepancy indicator: visual alert when `0x711` (hall sensor speed) and `0x720` (GPS speed) differ by a configurable percentage.
- LED ring: turn signal / hazard animation from `0x710`, ambient brightness from `0x726`.

---

### Body Controller — `esp32/` env: `body_controller`

**Role:** Central sensor hub. Reads vehicle GPIO inputs, drives hall sensor speed measurement, estimates gear, persists odometer, and bridges to BLE for the phone app.

**Components:**

| Component | Part / Model | Interface | ESP32 Pin | Notes |
|-----------|-------------|-----------|-----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | BLE built-in |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO5**, RX→**GPIO4** | 5V logic, needs 5V supply |
| Hall Effect Sensor | A3144 or OH137 | Interrupt | **GPIO27** | Driveshaft, 1 pulse/rev, pull-up |
| Key On Input | PC817 optocoupler | Digital In | **GPIO32** | 12V → 3.3V isolated |
| Brake Input | PC817 optocoupler | Digital In | **GPIO33** | 12V → 3.3V isolated |
| Regen Active Input | PC817 optocoupler | Digital In | **GPIO25** | 12V → 3.3V isolated |
| Fan Active Input | PC817 optocoupler | Digital In | **GPIO26** | 12V → 3.3V isolated |
| Reverse Gear Input | PC817 optocoupler | Digital In | **GPIO34** | Input-only pin (no pull-up, add external) |
| Left Turn Input | PC817 optocoupler | Digital In | **GPIO35** | Input-only pin (no pull-up, add external) |
| Right Turn Input | PC817 optocoupler | Digital In | **GPIO36** | Input-only pin (no pull-up, add external) |
| Voltage Regulator | LM2596 or similar | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | End-of-bus nodes only |

> **Pin note:** GPIO 34, 35, 36 are input-only on ESP32 (no internal pull-up). External pull-up resistors required on these pins. All optocoupler outputs are active-low.

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Consumes | `0x1DA` | LEAF_MOTOR_STATUS | Leaf → | — |
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |
| Broadcasts | `0x710` | BODY_STATE | → All | 10 Hz |
| Broadcasts | `0x711` | BODY_SPEED | → All | 10 Hz |
| Broadcasts | `0x712` | BODY_GEAR | → All | 2 Hz |
| Broadcasts | `0x713` | BODY_ODOMETER | → All | 1 Hz |

**Inputs:**
- 7 digital GPIO (with level shifting/optocouplers): Key On, Brake Pressed, Regen Active, Fan Active, Reverse Gear, Left Turn Signal, Right Turn Signal
- 1 hall effect sensor on driveshaft (1 pulse/rev, interrupt-driven, up to ~5.6 kHz at 100 mph)

**Behavior:**
- `0x710` BODY_STATE: Packs all 7 inputs + hazard flag into byte 0 bit flags. Hazard detection state machine: if left and right turn signals activate within a few ms, broadcasts HAZARD bit instead of individual LEFT+RIGHT.
- `0x711` BODY_SPEED: Authority source for vehicle speed. Computed from hall sensor pulse timing using build-time constants for differential ratio (3.96) and tire diameter (14").
- `0x712` BODY_GEAR: Compares motor RPM from Leaf `0x1DA` (bytes 1–2) against driveshaft RPM (from hall sensor) to estimate which of the MGB's 4-speed gears is engaged. Gear ratios: 1st=3.44, 2nd=2.17, 3rd=1.38, 4th=1.00, with configurable tolerance band. Unknown = 0xFF.
- `0x713` BODY_ODOMETER: 32-bit unsigned miles (little-endian). Persisted to ESP32 NVS every 0.5 mile.
- BLE: Acts as Bluetooth LE peripheral, exposing vehicle data for the phone app.

---

### Primary Display — `python/primary-display/`

**Role:** Main dashboard screen. Pi 4B + Waveshare 3.4" Round DSI LCD (800x800). Qt/QML with PySide6, GPU-accelerated via eglfs.

**Components:**

| Component | Part / Model | Interface | Pi Connection | Notes |
|-----------|-------------|-----------|---------------|-------|
| SBC | Raspberry Pi 4B (4GB+) | — | — | 64-bit Pi OS required for PySide6 |
| Display | Waveshare 3.4" Round DSI LCD | DSI | DSI ribbon cable | 800x800, 10-point capacitive touch |
| CAN Adapter | Innomaker USB2CAN | USB | USB-A port | gs_usb driver, SocketCAN |
| Storage | MicroSD 32GB+ Class 10 | — | MicroSD slot | |
| Power | 5V 3A USB-C supply | — | USB-C port | Delayed shutdown after key-off |

> **No GPIO pins consumed.** Display uses DSI ribbon, CAN uses USB, touch is integrated with the display.

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Consumes | `0x700` | HEARTBEAT | ← All | 1 Hz |
| Consumes | `0x710` | BODY_STATE | Body → | 10 Hz |
| Consumes | `0x711` | BODY_SPEED | Body → | 10 Hz |
| Consumes | `0x713` | BODY_ODOMETER | Body → | 1 Hz |
| Consumes | `0x1DB` | LEAF_BATTERY_STATUS | Leaf → | — |
| Consumes | `0x1DC` | LEAF_CHARGER_STATUS | Leaf → | — |
| Consumes | `0x55A` | LEAF_INVERTER_TEMPS | Leaf → | — |
| Consumes | `0x55B` | LEAF_SOC_PRECISE | Leaf → | — |
| Consumes | `0x5BC` | LEAF_BATTERY_HEALTH | Leaf → | — |
| Consumes | `0x5C0` | LEAF_BATTERY_TEMP | Leaf → | — |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | GPS → | 2 Hz |
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |

**Contexts (auto-switching based on vehicle state):**

- **Startup** — Custom boot splash during Pi boot (15–30 sec cold start). Transitions to Idle when ready.
- **Driving** — Range estimation arc gauge following display shape. Arc color shifts green→red based on Wh/mile efficiency. Current speed highlighted on arc. Center: estimated range at current speed. Forecasts at other speeds. Speed discrepancy alert when hall sensor and GPS speeds diverge.
- **Charging (Simple)** — SOC %, charge power (kW), estimated time to full, charge rate graph over time.
- **Charging (Detailed)** — Everything in Simple plus battery voltage, current, temperature, SOH, and 96 cell pair voltages + shunt status via UDS query (0x79B/0x7BB). Polled every 10–60 sec only when this view is active.
- **Idle** — Elapsed drive time, estimated range remaining, time remaining at that range, miles since last charge.
- **Diagnostics** — Grid of CAN messages with freshness color coding (green <1s, yellow <5s, orange 10+s). Layout iterated frequently during development.

**Alert system:** Bottom third of driving context. Shows alerts at or above configurable severity (DEBUG/INFO/WARN/ERROR/CRITICAL). Auto-acknowledged after 10 seconds. Sources: missing heartbeats, BMS warnings, temperature thresholds.

---

### GPS Display — `python/gps-display/`

**Role:** GPS receiver, time source, ambient light calculator, astronomical display. Pi 3B + Waveshare 2" Round LCD + NEO-6M GPS.

**Components:**

| Component | Part / Model | Interface | Pi GPIO | Notes |
|-----------|-------------|-----------|---------|-------|
| SBC | Raspberry Pi 3B | — | — | |
| Display | Waveshare 2" Round LCD | SPI | MOSI→**GPIO10**, SCLK→**GPIO11**, CS→**GPIO8**, DC→**GPIO25**, RST→**GPIO27**, BL→**GPIO18** | SPI0, backlight PWM on GPIO18 |
| GPS Receiver | NEO-6MV2 (u-blox) | UART | TX→**GPIO15** (RXD0), RX→**GPIO14** (TXD0) | 9600 baud, with ceramic antenna |
| CAN Adapter | Innomaker USB2CAN | USB | USB-A port | gs_usb driver, SocketCAN |
| Storage | MicroSD 16GB+ Class 10 | — | MicroSD slot | |
| Power | 5V 2.5A Micro-USB supply | — | Micro-USB port | Delayed shutdown after key-off |

> **GPIO pin map (BCM numbering):** SPI0 for display (GPIO 8, 10, 11 + GPIO 18, 25, 27 for control). UART0 for GPS (GPIO 14, 15). Serial console must be disabled in raspi-config to free UART0.

| | CAN ID | Name | Direction | Rate |
|---|--------|------|-----------|------|
| Broadcasts | `0x700` | HEARTBEAT | → All | 1 Hz |
| Broadcasts | `0x720` | GPS_SPEED | → All | 2 Hz |
| Broadcasts | `0x721` | GPS_TIME | → All | 2 Hz |
| Broadcasts | `0x722` | GPS_DATE | → All | 2 Hz |
| Broadcasts | `0x723` | GPS_LATITUDE | → All | 2 Hz |
| Broadcasts | `0x724` | GPS_LONGITUDE | → All | 2 Hz |
| Broadcasts | `0x725` | GPS_ELEVATION | → All | 2 Hz |
| Broadcasts | `0x726` | GPS_AMBIENT_LIGHT | → All | 2 Hz |

**Behavior:**
- GPS: NEO-6MV2 over UART at 9600 baud. On first fix, sets Pi system time from GPS (timezone from geolocation).
- Display before fix: "Waiting on Fix..."
- Display after fix: 24-hour rim (noon top, midnight bottom), yellow sunrise→sunset, dark blue sunset→sunrise with twilight gradients. White inner border where moon is above horizon. Center: moon phase icon, bold HH:MM time, day of week.
- Almanac (sunrise/sunset/moonrise/moonset/moon phase) computed locally from GPS lat/lon + date — no internet required.
- `0x726` ambient light category: DAYLIGHT (0), EARLY_TWILIGHT (1), LATE_TWILIGHT (2), DARKNESS (3). Computed from current time relative to sunset. All gauge modules consume this to set LED backlight level.

---

### Test / Monitor Pi — `python/tools/`

**Role:** Dedicated bench Pi for CAN bus testing and diagnostics. Runs CLI Python tools.

**Components:**

| Component | Part / Model | Interface | Pi Connection | Notes |
|-----------|-------------|-----------|---------------|-------|
| SBC | Raspberry Pi 3B+ or 4B | — | — | Any model with USB |
| CAN Adapter | Innomaker USB2CAN | USB | USB-A port | gs_usb driver, SocketCAN |
| Storage | MicroSD 16GB+ Class 10 | — | MicroSD slot | |
| Power | 5V USB supply | — | USB port | Bench use only |

> **No GPIO pins consumed.** CAN adapter is USB. No display needed — all tools are CLI.

---

### Phone App — `phone-app/`

**Role:** Mobile dashboard consuming BLE data from the Body Controller.

- Progressive Web App (PWA) using Web Bluetooth API — runs in any modern browser, no app store.
- Connects to Body Controller as BLE central.
- Displays live vehicle data: speed, SOC, gear, temps, odometer.

---

## CAN Bus Reference

### Custom CAN IDs (0x700–0x73F)

| ID | Name | Source | Rate | Payload |
|----|------|--------|------|---------|
| `0x700` | HEARTBEAT | All modules | 1 Hz | `[role(5B)] [uptime(1B)] [errors(1B)] [rsvd(1B)]` |
| `0x710` | BODY_STATE | Body Controller | 10 Hz | `[flags(1B)] [rsvd(7B)]` — see bit flags below |
| `0x711` | BODY_SPEED | Body Controller | 10 Hz | `[speed(8B)]` — 64-bit double, mph |
| `0x712` | BODY_GEAR | Body Controller | 2 Hz | `[gear(1B)] [reverse(1B)] [rsvd(6B)]` |
| `0x713` | BODY_ODOMETER | Body Controller | 1 Hz | `[miles(4B)] [rsvd(4B)]` — uint32 LE |
| `0x720` | GPS_SPEED | GPS Display | 2 Hz | `[speed(8B)]` — 64-bit double, mph |
| `0x721` | GPS_TIME | GPS Display | 2 Hz | `[time(8B)]` — 64-bit double, sec since midnight UTC |
| `0x722` | GPS_DATE | GPS Display | 2 Hz | `[date(8B)]` — 64-bit double, days since 2000-01-01 |
| `0x723` | GPS_LATITUDE | GPS Display | 2 Hz | `[lat(8B)]` — 64-bit double, decimal degrees |
| `0x724` | GPS_LONGITUDE | GPS Display | 2 Hz | `[lon(8B)]` — 64-bit double, decimal degrees |
| `0x725` | GPS_ELEVATION | GPS Display | 2 Hz | `[elev(8B)]` — 64-bit double, meters ASL |
| `0x726` | GPS_AMBIENT_LIGHT | GPS Display | 2 Hz | `[cat(1B)] [rsvd(7B)]` — 0–3 |
| `0x730` | SELF_TEST | Any (diagnostic) | On-demand | `[target(1B)] [rsvd(7B)]` — 0xFF=ALL or LogRole enum value |
| `0x731` | LOG | All modules | On-event | `[role:level(1B)] [event(1B)] [context(4B BE)] [rsvd(1B)] [textFrames(1B)]` |
| `0x732` | LOG_TEXT | All modules | On-event | `[fragIndex(1B)] [ascii(7B)]` — up to 7 continuation frames |
| `0x733`–`0x73F` | *Reserved* | — | — | Future use |

#### BODY_STATE Bit Flags (byte 0 of `0x710`)

| Bit | Flag | Meaning |
|-----|------|---------|
| 0 | KEY_ON | Ignition key is on |
| 1 | BRAKE_PRESSED | Brake pedal pressed |
| 2 | REGEN_ACTIVE | Regenerative braking active |
| 3 | FAN_ACTIVE | Cooling fan running |
| 4 | REVERSE_GEAR | Reverse gear engaged |
| 5 | LEFT_TURN | Left turn signal active |
| 6 | RIGHT_TURN | Right turn signal active |
| 7 | HAZARD | Hazard lights active (overrides LEFT+RIGHT) |

#### Heartbeat Roles (bytes 0–4 of `0x700`)

| Role | ASCII (space-padded) | Module |
|------|---------------------|--------|
| `FUEL ` | `46 55 45 4C 20` | Fuel/SOC servo gauge |
| `AMPS ` | `41 4D 50 53 20` | Amps servo gauge |
| `TEMP ` | `54 45 4D 50 20` | Temperature servo gauge |
| `SPEED` | `53 50 45 45 44` | Speedometer |
| `BODY ` | `42 4F 44 59 20` | Body controller |
| `DASH ` | `44 41 53 48 20` | Primary display Pi |
| `GPS  ` | `47 50 53 20 20` | GPS display Pi |

#### Ambient Light Categories (byte 0 of `0x726`)

| Value | Name | Description |
|-------|------|-------------|
| 0 | DAYLIGHT | Full daylight |
| 1 | EARLY_TWILIGHT | Sun recently set |
| 2 | LATE_TWILIGHT | Deep twilight |
| 3 | DARKNESS | Full darkness |

#### LOG Frame Format (`0x731`)

Structured log event emitted by any module on boot, error, self-test, etc. Falls back to Serial when CAN is unavailable.

| Byte | Field | Description |
|------|-------|-------------|
| 0 | role:level | High nibble = LogRole (0–6), low nibble = LogLevel (0–4) |
| 1 | event | LogEvent code (see [`common/cpp/log_events.h`](common/cpp/log_events.h)) |
| 2–5 | context | 32-bit unsigned context value, big-endian (e.g. `millis()`, error code) |
| 6 | reserved | 0x00 |
| 7 | textFrames | Number of LOG_TEXT continuation frames to follow (0–7) |

#### LOG_TEXT Frame Format (`0x732`)

Optional text continuation. Up to 7 frames (49 ASCII chars) following a LOG frame.

| Byte | Field | Description |
|------|-------|-------------|
| 0 | fragIndex | Fragment index (0–6) |
| 1–7 | ascii | 7 bytes of null-padded ASCII text |

#### Log Levels

| Value | Name | Usage |
|-------|------|-------|
| 0 | DEBUG | Verbose diagnostic info |
| 1 | INFO | Normal events (boot, self-test pass) |
| 2 | WARN | CAN silence, sensor timeout |
| 3 | ERROR | TX failure, init failure |
| 4 | CRITICAL | Boot start, watchdog reset |

---

### Leaf EV-CAN IDs (AZE0, 2013–2017)

These are native Leaf messages present on the EV-CAN bus. Dashboard modules consume them read-only.

| ID | Name | Key Signals |
|----|------|-------------|
| `0x1DA` | LEAF_MOTOR_STATUS | MotorRPM (bytes 1–2, signed 16-bit), AvailableTorque, FailSafe |
| `0x1DB` | LEAF_BATTERY_STATUS | BatteryVoltage (bytes 0–1, 10-bit, x0.5 V), BatteryCurrent (bytes 2–3, 11-bit signed, x0.5 A), SOC (byte 4, %) |
| `0x1DC` | LEAF_CHARGER_STATUS | ChargePower (bytes 0–1, 10-bit, x0.25 kW) |
| `0x390` | LEAF_VCM_STATUS | VCMMainRelay (byte 4, bit 0) |
| `0x55A` | LEAF_INVERTER_TEMPS | MotorTemp (byte 0), IGBTTemp (byte 1), InverterTemp (byte 2) — each x0.5 = Celsius |
| `0x55B` | LEAF_SOC_PRECISE | SOC (bytes 0–1, unsigned 16-bit, x0.01 = %) |
| `0x5BC` | LEAF_BATTERY_HEALTH | GIDs (bytes 0–1, 10-bit), SOH (byte 4, bits 1–7, %) |
| `0x5C0` | LEAF_BATTERY_TEMP | BatteryTemp (byte 0, signed, offset -40 = Celsius) |
| `0x59E` | LEAF_AZE0_IDENTIFIER | Presence confirms AZE0 generation (2013–2017) |

### Resolve EV Controller

Optional future VCU. CAN definitions are included for forward compatibility.

| ID | Name | Key Signals |
|----|------|-------------|
| `0x539` | RESOLVE_DISPLAY_MSG | Gear (byte 0, bits 0–3), IgnitionOn (bit 4), SystemOn (bit 5), DisplayMaxChargeOn (bit 6), RegenStrength (byte 1), SOCforDisplay (byte 2, %) |

---

## CAN Message Flow Diagram

```
Leaf EV-CAN (native)            Custom Dashboard Messages
─────────────────────           ──────────────────────────

0x1DA Motor Status ──────────►  Body Controller ──► 0x710 BODY_STATE (10 Hz)
                         │                     ├──► 0x711 BODY_SPEED (10 Hz)
                         │    (+ hall sensor    ├──► 0x712 BODY_GEAR  (2 Hz)
                         │      + GPIO inputs)  └──► 0x713 BODY_ODOMETER (1 Hz)
                         │
0x1DB Battery Status ────┼───►  Fuel Gauge (servo + LEDs)
                         │
0x55A Inverter Temps ────┼───►  Temp Gauge (servo + LEDs)
                         │
0x55B Precise SOC ───────┼───►  Primary Display
0x5BC Battery Health ────┤         (all contexts)
0x5C0 Battery Temp ──────┤
0x1DC Charger Status ────┤
0x390 VCM Status ────────┘

GPS Display ─────────────────►  0x720 GPS_SPEED (2 Hz)
  (NEO-6M + almanac)       ├──► 0x721 GPS_TIME  (2 Hz)
                            ├──► 0x722 GPS_DATE  (2 Hz)
                            ├──► 0x723 GPS_LATITUDE  (2 Hz)
                            ├──► 0x724 GPS_LONGITUDE (2 Hz)
                            ├──► 0x725 GPS_ELEVATION (2 Hz)
                            └──► 0x726 GPS_AMBIENT_LIGHT (2 Hz)

All Modules ─────────────────►  0x700 HEARTBEAT (1 Hz each)
```

---

## Shared CAN Definitions (Single Source of Truth)

All CAN IDs, payload formats, decode constants, and signal definitions live in `common/`:

| File | Purpose |
|------|---------|
| `common/can_ids.json` | Master definition — all custom IDs, Leaf IDs, Resolve IDs, heartbeat roles |
| `common/cpp/can_ids.h` | C++ constants — custom IDs, bit flags, range guards, roles |
| `common/cpp/leaf_messages.h` | C++ decode — byte offsets, bit positions, scaling factors per Leaf message |
| `common/cpp/resolve_messages.h` | C++ decode — Resolve EV 0x539 |
| `common/python/can_ids.py` | Python mirror of `can_ids.h` |
| `common/python/leaf_messages.py` | Python decode functions + dispatcher for all Leaf messages |
| `common/python/resolve_messages.py` | Python decode for Resolve 0x539 |

The JSON file is canonical. The C++ and Python files are manually-maintained mirrors (a code generator is a future item).

---

## Project Structure

```
mgb-dash-2026/
├── common/                     Single source of truth for CAN definitions
│   ├── can_ids.json            Master CAN ID definitions
│   ├── cpp/                    C++ headers (ESP32 firmware)
│   │   ├── can_ids.h
│   │   ├── leaf_messages.h
│   │   └── resolve_messages.h
│   └── python/                 Python modules (Pi applications + tools)
│       ├── can_ids.py
│       ├── leaf_messages.py
│       └── resolve_messages.py
│
├── esp32/                      All ESP32 PlatformIO code
│   ├── platformio.ini          5 build environments
│   ├── src/
│   │   ├── servo_gauge/        Shared main for FUEL/AMPS/TEMP
│   │   ├── speedometer/        Speedometer main
│   │   └── body_controller/    Body controller main
│   └── lib/                    Shared libraries (PlatformIO auto-discovers)
│       ├── CanBus/             TWAI driver, TX guard, bus-off recovery
│       ├── Heartbeat/          1 Hz heartbeat broadcaster
│       ├── LedRing/            WS2812B driver, animations, ambient blending
│       ├── ServoGauge/         Servo control with EMA smoothing
│       └── LeafCan/            Leaf + Resolve CAN message decoders
│
├── python/                     All Python applications and tools
│   ├── primary-display/        Pi 4B — pycairo + pygame
│   ├── gps-display/            Pi 3B — Python + NEO-6M GPS
│   └── tools/                  CLI diagnostic tools (test/monitor Pi)
│       ├── can_monitor.py      Decoded CAN traffic viewer
│       ├── can_emulate.py      Module emulator
│       ├── can_inject.py       Send single CAN frames
│       ├── can_replay.py       Record/playback sessions
│       ├── can_stress.py       Bus load testing
│       ├── can_cell_query.py   UDS cell voltage/shunt query
│       └── can_scan.py         Bus discovery / module detection
│
├── phone-app/                  PWA — Web Bluetooth
│
└── pi-setup/                   Pi provisioning scripts
    ├── base.sh                 Common (SocketCAN, python-can, git)
    ├── primary-display.sh      Dash Pi (64-bit, PySide6, DSI)
    ├── gps-display.sh          GPS Pi (UART, GPS, SPI display)
    └── test-monitor.sh         Test Pi (USB2CAN, tools)
```

## Building Firmware

```bash
cd esp32
pio run                          # Build all 5 environments
pio run -e servo_fuel            # Build one environment
pio run -e servo_fuel -t upload  # Flash via USB
```

All three servo gauges share one codebase (`src/servo_gauge/main.cpp`) differentiated by build-time constants (`GAUGE_ROLE=FUEL/AMPS/TEMP`). Speedometer and body controller have separate source directories.

---

## Development Status

### Implemented

| Module | Status | Notes |
|--------|--------|-------|
| **Body Controller** | Loop complete | GPIO reading, hazard state machine, hall sensor speed, gear estimation, odometer/NVS, CAN broadcast (0x710–0x713), CAN receive (0x1DA motor RPM, 0x730 self-test) |
| **Servo Gauges (x3)** | Loop complete | CAN decode per role (FUEL→0x55B/0x1DB, AMPS→0x1DB, TEMP→0x5C0), servo mapping with per-role range/smoothing, LED ring threshold warnings, turn signal/hazard animations with 600 ms holdoff, ambient light from 0x726, stale data detection, CAN silence watchdog |
| **LeafCan decoder** | Complete | All 9 Leaf + Resolve CAN messages decoded with ESP_LOGD debug logging per method |
| **Primary Display** | Phase 1+2 complete | pycairo+pygame, diagnostics grid with 41 signals, freshness colors, heartbeat bar, scroll |
| **GPS Display** | Fully ported | 24hr clock dial, sun/moon arcs, CAN broadcast (0x720–0x726), ambient light |
| **Shared Libraries** | Complete | CanBus, Heartbeat, CanLog, LedRing, ServoGauge, LeafCan |
| **Code Generator** | Complete | `python/tools/codegen.py`: JSON → Python modules |

### Not Yet Implemented

- Speedometer loop (stepper + eInk + servo gear indicator)
- Primary Display Phase 3 (ReplaySource) and Phase 4 (CanBusSource + remaining contexts)
- Phone app BLE and UI logic
- Tool scripts (stubs only — no python-can integration)
- Pi setup scripts (untested on hardware)
- CI/CD, testing infrastructure, git hooks
- C++ header code generator (Python codegen done)
- Hardware integration testing
