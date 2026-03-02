# CAN Bus Reference

Single shared CAN bus at **500 kbps**, 11-bit standard IDs. All modules sit directly on the Nissan Leaf EV-CAN. Custom dashboard messages coexist with Leaf-native traffic in the reserved **0x700–0x73F** range (above all Leaf EV-CAN IDs, below OBD-II).

The canonical definition for all CAN IDs, payloads, and decode constants is [`can_ids.json`](can_ids.json).

## Custom CAN IDs (0x700–0x73F)

| ID | Name | Source | Rate | Payload |
|----|------|--------|------|---------|
| `0x700` | HEARTBEAT | All modules | 1 Hz | `[role(5B)] [uptime(1B)] [errors(1B)] [rsvd(1B)]` |
| `0x710` | BODY_STATE | Body Controller | 10 Hz | `[flags0(1B)] [flags1(1B)] [rsvd(6B)]` — see bit flags below |
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
| `0x727` | GPS_UTC_OFFSET | GPS Display | 2 Hz | `[offset(2B)] [rsvd(6B)]` — int16 LE, minutes (e.g. -300=EST) |
| `0x730` | SELF_TEST | Any (diagnostic) | On-demand | `[target(1B)] [rsvd(7B)]` — 0xFF=ALL or role char |
| `0x731` | LOG | All modules | On-event | `[role:level(1B)] [event(1B)] [context(4B BE)] [rsvd(1B)] [textFrames(1B)]` |
| `0x732` | LOG_TEXT | All modules | On-event | `[fragIndex(1B)] [ascii(7B)]` — up to 7 continuation frames |
| `0x733`–`0x73F` | *Reserved* | — | — | Future use |

### BODY_STATE Bit Flags

**Byte 0** (`0x710`)

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

**Byte 1** (`0x710`)

| Bit | Flag | Meaning |
|-----|------|---------|
| 0 | KEY_START | Starter engaged |
| 1 | KEY_ACCESSORY | Accessory position |
| 2 | RUNNING_LIGHTS | Running lights on |
| 3 | HEADLIGHTS | Headlights on |
| 4 | CHARGE_PORT | Charge port open |

### Heartbeat Roles (bytes 0–4 of `0x700`)

| Role | ASCII (space-padded) | Module |
|------|---------------------|--------|
| `FUEL ` | `46 55 45 4C 20` | Fuel/SOC servo gauge |
| `AMPS ` | `41 4D 50 53 20` | Amps servo gauge |
| `TEMP ` | `54 45 4D 50 20` | Temperature servo gauge |
| `SPEED` | `53 50 45 45 44` | Speedometer |
| `BODY ` | `42 4F 44 59 20` | Body controller |
| `DASH ` | `44 41 53 48 20` | Primary display Pi |
| `GPS  ` | `47 50 53 20 20` | GPS display Pi |

### Ambient Light Categories (byte 0 of `0x726`)

| Value | Name | Description |
|-------|------|-------------|
| 0 | DAYLIGHT | Full daylight |
| 1 | EARLY_TWILIGHT | Sun recently set |
| 2 | LATE_TWILIGHT | Deep twilight |
| 3 | DARKNESS | Full darkness |

### LOG Frame Format (`0x731`)

Structured log event emitted by any module on boot, error, self-test, etc. Falls back to Serial when CAN is unavailable.

| Byte | Field | Description |
|------|-------|-------------|
| 0 | role:level | High nibble = LogRole (0–6), low nibble = LogLevel (0–4) |
| 1 | event | LogEvent code (see [`common/cpp/log_events.h`](cpp/log_events.h)) |
| 2–5 | context | 32-bit unsigned context value, big-endian (e.g. `millis()`, error code) |
| 6 | reserved | 0x00 |
| 7 | textFrames | Number of LOG_TEXT continuation frames to follow (0–7) |

### LOG_TEXT Frame Format (`0x732`)

Optional text continuation. Up to 7 frames (49 ASCII chars) following a LOG frame.

| Byte | Field | Description |
|------|-------|-------------|
| 0 | fragIndex | Fragment index (0–6) |
| 1–7 | ascii | 7 bytes of null-padded ASCII text |

### Log Levels

| Value | Name | Usage |
|-------|------|-------|
| 0 | DEBUG | Verbose diagnostic info |
| 1 | INFO | Normal events (boot, self-test pass) |
| 2 | WARN | CAN silence, sensor timeout |
| 3 | ERROR | TX failure, init failure |
| 4 | CRITICAL | Boot start, watchdog reset |

---

## Leaf EV-CAN IDs (AZE0, 2013–2017)

Native Leaf messages present on the EV-CAN bus. Dashboard modules consume them read-only.

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
                            ├──► 0x726 GPS_AMBIENT_LIGHT (2 Hz)
                            └──► 0x727 GPS_UTC_OFFSET (2 Hz)

All Modules ─────────────────►  0x700 HEARTBEAT (1 Hz each)
```

---

## Shared CAN Definitions (Single Source of Truth)

All CAN IDs, payload formats, decode constants, and signal definitions live in `common/`:

| File | Purpose |
|------|---------|
| [`can_ids.json`](can_ids.json) | Master definition — all custom IDs, Leaf IDs, Resolve IDs, heartbeat roles |
| [`cpp/can_ids.h`](cpp/can_ids.h) | C++ constants — custom IDs, bit flags, range guards, roles |
| [`cpp/leaf_messages.h`](cpp/leaf_messages.h) | C++ decode — byte offsets, bit positions, scaling factors per Leaf message |
| [`cpp/resolve_messages.h`](cpp/resolve_messages.h) | C++ decode — Resolve EV 0x539 |
| [`python/can_ids.py`](python/can_ids.py) | Python mirror of `can_ids.h` |
| [`python/leaf_messages.py`](python/leaf_messages.py) | Python decode functions + dispatcher for all Leaf messages |
| [`python/resolve_messages.py`](python/resolve_messages.py) | Python decode for Resolve 0x539 |

### Code Generator

The JSON file is canonical. Python modules are auto-generated:

```powershell
python python/tools/codegen.py
```

This regenerates `can_ids.py`, `leaf_messages.py`, and `resolve_messages.py`. Do **not** edit these files by hand — changes will be overwritten. C++ headers are currently maintained manually.
