# MGB Dash 2026

CAN bus dashboard controller for a Nissan Leaf EV conversion in an MGB body. Seven modules communicate over a single shared CAN bus: three servo gauges (fuel/amps/temp), a speedometer, a body controller, a primary display, and a GPS display. A phone app connects over BLE, and a test Pi provides CLI diagnostic tools.

## Architecture

<img src="docs/images/rev2.jpg" alt="Latest version" width="600">

<img src="docs/images/dash.JPG" alt="Dash faceplate" width="600">

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

| Module | Hardware | Path | Description |
|--------|----------|------|-------------|
| [Fuel Gauge](esp32/src/servo_gauge/README.md) | ESP32 + servo + 12 LEDs | `esp32/` env: `servo_fuel` | Battery SOC on 180° servo needle with LED ring |
| [Amps Gauge](esp32/src/servo_gauge/README.md) | ESP32 + servo + 12 LEDs | `esp32/` env: `servo_amps` | Battery current (center-zero) with LED ring |
| [Temp Gauge](esp32/src/servo_gauge/README.md) | ESP32 + servo + 12 LEDs | `esp32/` env: `servo_temp` | Battery/inverter temperature with LED ring |
| [Speedometer](esp32/src/speedometer/README.md) | ESP32 + stepper + servo + eInk | `esp32/` env: `speedometer` | Slot-machine speed drum, gear indicator, odometer |
| [Body Controller](esp32/src/body_controller/README.md) | ESP32 + GPIO + hall sensor | `esp32/` env: `body_controller` | Sensor hub: speed, gear, odometer, BLE bridge |
| [Primary Display](python/primary-display/README.md) | Pi 4B + 3.4" DSI LCD | `python/primary-display/` | Main dash screen: pycairo + pygame, 5 contexts |
| [GPS Display](python/gps-display/README.md) | Pi 3B + 2" SPI LCD + NEO-6M | `python/gps-display/` | 24hr clock dial, sun/moon arcs, ambient light |
| [Phone App](phone-app/README.md) | Mobile browser | `phone-app/` | PWA with Web Bluetooth (scaffold) |
| [Diagnostic Tools](python/tools/README.md) | Any Pi + USB2CAN | `python/tools/` | CLI tools for CAN testing and diagnostics |
| [Pi Setup](pi-setup/README.md) | — | `pi-setup/` | Provisioning scripts for all Pis |

---

## CAN Bus

Full CAN protocol reference (payload layouts, bit flags, Leaf message decoding, message flow diagram) is in **[common/README.md](common/README.md)**.

Custom IDs use the **0x700–0x73F** range:

| ID | Name | Source | Rate |
|----|------|--------|------|
| `0x700` | HEARTBEAT | All modules | 1 Hz |
| `0x710` | BODY_STATE | Body Controller | 10 Hz |
| `0x711` | BODY_SPEED | Body Controller | 10 Hz |
| `0x712` | BODY_GEAR | Body Controller | 2 Hz |
| `0x713` | BODY_ODOMETER | Body Controller | 1 Hz |
| `0x720` | GPS_SPEED | GPS Display | 2 Hz |
| `0x721` | GPS_TIME | GPS Display | 2 Hz |
| `0x722` | GPS_DATE | GPS Display | 2 Hz |
| `0x723`–`0x725` | GPS_LAT/LON/ELEV | GPS Display | 2 Hz |
| `0x726` | GPS_AMBIENT_LIGHT | GPS Display | 2 Hz |
| `0x727` | GPS_UTC_OFFSET | GPS Display | 2 Hz |
| `0x730` | SELF_TEST | Any | On-demand |
| `0x731`–`0x732` | LOG / LOG_TEXT | All modules | On-event |

---

## Project Structure

```
mgb-dash-2026/
├── common/                     CAN definitions (single source of truth)
│   ├── can_ids.json            Master CAN ID definitions
│   ├── cpp/                    C++ headers (ESP32 firmware)
│   └── python/                 Python modules (auto-generated)
├── esp32/                      All ESP32 PlatformIO code
│   ├── platformio.ini          5 build environments
│   ├── src/                    servo_gauge/, speedometer/, body_controller/
│   └── lib/                    CanBus, Heartbeat, LedRing, ServoGauge, LeafCan, StepperWheel
├── python/
│   ├── primary-display/        Pi 4B — pycairo + pygame
│   ├── gps-display/            Pi 3B — Python + NEO-6M GPS
│   └── tools/                  CLI diagnostic tools + codegen
├── phone-app/                  PWA — Web Bluetooth (scaffold)
├── pi-setup/                   Pi provisioning scripts
└── docs/                       Images, pinout diagrams, vehicle specs
```

## Building

### ESP32 Firmware

```powershell
cd esp32
pio run                          # Build all 5 environments
pio run -e servo_fuel            # Build one environment
pio run -e servo_fuel -t upload  # Flash via USB
```

All three servo gauges share one codebase (`src/servo_gauge/main.cpp`) differentiated by build-time `GAUGE_ROLE` constant.

### Python

All Python packages use `uv` + `pyproject.toml`:

```powershell
cd python/primary-display
uv sync
uv run python main.py --source synthetic
```

After editing `common/can_ids.json`, regenerate Python modules:

```powershell
python python/tools/codegen.py
```

---

## Development Status

### Implemented

| Module | Status | Notes |
|--------|--------|-------|
| **Body Controller** | Loop complete | GPIO reading, hazard state machine, hall sensor speed, gear estimation, odometer/NVS, CAN broadcast (0x710–0x713), CAN receive (0x1DA, 0x730) |
| **Servo Gauges (x3)** | Loop complete | CAN decode per role, servo mapping, LED ring warnings, turn signal/hazard animations, ambient light, stale data detection |
| **Speedometer** | Loop complete | Stepper needle (CAN-driven), servo gear indicator, turn signal/hazard LEDs, ambient light, self-test |
| **LeafCan decoder** | Complete | All 9 Leaf + Resolve CAN messages decoded |
| **Primary Display** | Phase 1+2 complete | pycairo+pygame, 5 contexts, alert system, CAN receive, clock sync |
| **GPS Display** | Fully ported | 24hr clock dial, sun/moon arcs, CAN broadcast (0x720–0x727), ambient light, backlight PWM |
| **Shared Libraries** | Complete | CanBus, Heartbeat, CanLog, LedRing, ServoGauge, StepperWheel, LeafCan |
| **Code Generator** | Complete | `python/tools/codegen.py`: JSON → Python modules + C++ headers |

### Not Yet Implemented

- eInk odometer driver (speedometer has TODO placeholder)
- Primary Display Phase 3 (ReplaySource)
- Phone app BLE and UI logic
- Tool scripts (stubs only — no python-can integration)
- CI/CD, testing infrastructure, git hooks
- Hardware integration testing
