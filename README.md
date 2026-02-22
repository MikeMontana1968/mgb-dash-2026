# MGB Dash 2026

CAN bus dashboard controller for a Nissan Leaf EV conversion in an MGB body.

## Modules

| Module | Hardware | Directory |
|--------|----------|-----------|
| Primary Display | Pi 4B + Waveshare 3.4" Round DSI LCD | `primary-display/` |
| Servo Gauges (x3) | ESP32 + TJA1050 + 180° servo + WS2812B ring | `firmware/` (env: servo_fuel, servo_amps, servo_temp) |
| Speedometer | ESP32 + TJA1050 + stepper + eInk + WS2812B ring | `firmware/` (env: speedometer) |
| Body Controller | ESP32 + TJA1050 + GPIO inputs + hall sensor + BLE | `firmware/` (env: body_controller) |
| GPS Display | Pi 3B + Waveshare 2" Round LCD + NEO-6M GPS | `gps-display/` |
| Phone App | PWA with Web Bluetooth | `phone-app/` |

## CAN Bus

- Single shared bus at 500 kbps, direct on Leaf EV-CAN
- 11-bit standard CAN IDs
- Custom IDs: 0x700–0x73F (see `common/can_ids.json`)
- Target: 2013 Leaf drivetrain + 2014 battery (AZE0)

## Building Firmware

```bash
cd firmware
pio run                    # Build all environments
pio run -e servo_fuel      # Build one environment
pio run -e servo_fuel -t upload  # Flash via USB
```

## Project Structure

- `common/` — Single source of truth for CAN definitions (JSON, C++, Python)
- `firmware/` — All ESP32 PlatformIO code and shared libraries
- `primary-display/` — Pi 4B Qt/QML dashboard
- `gps-display/` — Pi 3B GPS + clock display
- `phone-app/` — PWA mobile dashboard
- `tools/` — CLI diagnostic tools for test/monitor Pi
- `pi-setup/` — Pi provisioning scripts
