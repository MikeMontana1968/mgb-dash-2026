# Servo Gauges (Fuel / Amps / Temp)

Three 2-inch analog gauges driven by ESP32 + TJA1050 CAN transceiver. Each has a 180-degree servo needle and a 12-LED SK6812 RGBW ring for warnings and ambient lighting. All three share one codebase (`servo_gauge/main.cpp`), differentiated by build-time `GAUGE_ROLE` constant.

<img src="../../../docs/images/fuel.JPG" alt="Fuel gauge" width="400">

## Components

| Component | Part / Model | Interface | Fuel Pin | Amps Pin | Temp Pin | Notes |
|-----------|-------------|-----------|----------|----------|----------|-------|
| MCU | ESP32-WROOM-32 DevKit | — | — | — | — | |
| CAN Transceiver | TJA1050 | TWAI | TX→**GPIO12**, RX→**GPIO26** | TX→**GPIO12**, RX→**GPIO26** | TX→**GPIO12**, RX→**GPIO26** | 5V logic, needs 5V supply |
| Servo Motor | SG90 or MG90S, 180° | PWM | **GPIO27** | **GPIO27** | **GPIO14** | LEDC channel |
| LED Ring | SK6812 RGBW, 12 LEDs | Data | **GPIO14** | **GPIO14** | **GPIO27** | Adafruit NeoPixel (NEO_GRBW) |
| Voltage Regulator | LM2596 or similar | — | — | — | — | Vehicle 12V → 5V |
| CAN Termination | 120 ohm resistor | — | — | — | — | End-of-bus nodes only |

## CAN Messages

| Direction | CAN ID | Name | Rate |
|-----------|--------|------|------|
| Consumes | `0x1DB` | LEAF_BATTERY_STATUS | — |
| Consumes | `0x55B` | LEAF_SOC_PRECISE | — |
| Consumes | `0x5C0` | LEAF_BATTERY_TEMP | — |
| Consumes | `0x710` | BODY_STATE | 10 Hz |
| Consumes | `0x726` | GPS_AMBIENT_LIGHT | 2 Hz |
| Broadcasts | `0x700` | HEARTBEAT | 1 Hz |

> Not all IDs apply to every role — Fuel uses `0x55B`/`0x1DB`, Amps uses `0x1DB`, Temp uses `0x5C0`. All consume `0x710` (turn signals) and `0x726` (ambient light).

See [common/README.md](../../../common/README.md) for full payload details.

## Behavior

### Fuel Gauge (`servo_fuel`)

- Servo: 0–180° maps to 0–100% SOC. Primary source: precise SOC from `0x55B`; falls back to coarse SOC from `0x1DB` if precise is stale (>1 s). Smoothing τ=0.8 s.
- LED ring: red (<10% SOC — critically low), amber (<20% — low), ambient otherwise. Amber if CAN data stale >2 s.

### Amps Gauge (`servo_amps`)

- Servo: 0–180° maps -100 A (regen) to +200 A (discharge). Smoothing τ=0.3 s (snappy — current changes fast).
- Current sourced from `0x1DB` bytes 2–3 (upper 11 bits, signed, factor 0.5). Positive = discharge, negative = regen.
- LED ring: red (>150 A absolute — extreme current), amber (>100 A absolute — high current), ambient otherwise.

### Temp Gauge (`servo_temp`)

- Source: `0x5C0` battery temperature (byte 0, signed, offset -40 = °C).
- Servo: 0–180° maps -10 °C to 50 °C. Smoothing τ=1.0 s (slow — temp changes very gradually).
- LED ring: red (>45 °C or <-5 °C — extreme), amber (>35 °C or <0 °C — concerning), ambient otherwise.

### Common (all roles)

- Turn signal / hazard animation overlays from `0x710` body flags, with 600 ms holdoff to bridge relay blink gaps. Priority: hazard > left > right.
- Ambient white backlight level driven by `0x726` (DAYLIGHT=dim, DARKNESS=bright).
- CAN silence watchdog: blue breathing pulse if no CAN traffic within 5 s of boot.
- Amber LED ring if CAN data stale >2 s.

## Build

```powershell
cd esp32
pio run -e servo_fuel       # Build fuel gauge
pio run -e servo_amps       # Build amps gauge
pio run -e servo_temp       # Build temp gauge
pio run -e servo_fuel -t upload   # Flash via USB
```

## Pinout

- [Fuel pinout](../../../docs/servo_fuel-pinout.png)
- [Amps pinout](../../../docs/servo_amps-pinout.png)
- [Temp pinout](../../../docs/servo_temp-pinout.png)
