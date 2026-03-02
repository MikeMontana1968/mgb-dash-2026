# Phone App — MGB Diagnostics PWA

CAN bus diagnostics tool for the MGB EV dashboard. Runs as a Progressive Web App in Chrome on any phone, tablet, or desktop browser. Zero dependencies, no build step.

## Usage

**Demo mode** (default): Open `index.html` in Chrome. Synthetic data starts immediately — all 41 signals update with sinusoidal test values at 10 Hz. GPS heartbeat drops out periodically to demonstrate staleness detection.

**BLE mode**: Tap the BLE button to connect to the body controller ESP32 via Web Bluetooth. Requires HTTPS (or localhost). The ESP32 BLE bridge firmware is a future task — the connection code is implemented but untestable until then.

### Verification checklist

1. Open `phone-app/index.html` in Chrome
2. All 41 signals visible with updating values and freshness colors
3. Heartbeat bar shows 7 modules, GPS periodically goes stale (gray dot)
4. Tap group headers to collapse/expand
5. Resize browser: single-column on mobile, two-column on tablet/desktop
6. BLE button shows browser device picker (or status message on HTTP)

## File Structure

```
phone-app/
  index.html              App shell
  manifest.json           PWA manifest with inline SVG icon
  sw.js                   Service worker (cache-first offline)
  css/
    style.css             Dark theme, responsive grid, freshness colors
  js/
    app.js                Entry: init, mode switching, 4 Hz render loop
    vehicle-state.js      Signal + heartbeat store with timestamps
    can-decoder.js        CAN frame decode (port of base.py routing)
    demo-source.js        Synthetic data (port of synthetic_source.py)
    ble-source.js         Web Bluetooth connect + CAN relay notifications
    ui.js                 DOM rendering: signal groups, heartbeat bar
```

## Signal Groups

8 groups matching the primary display diagnostics context:

| Group | Signals | CAN IDs |
|-------|---------|---------|
| LEAF MOTOR | RPM, Torque, Failsafe | 1DA |
| LEAF BATTERY | Voltage, Current, SOC, SOC Precise, GIDs, SOH, Batt Temp | 1DB/55B/5BC/5C0 |
| LEAF CHARGER | Charge Power | 1DC |
| LEAF TEMPS | Motor, IGBT, Inverter | 55A |
| LEAF VCM | Main Relay | 390 |
| RESOLVE | Gear, Ignition, System, Regen, SOC | 539 |
| BODY | Key On, Brake, Regen, Reverse, Left Turn, Speed, Gear, Odo | 710-713 |
| GPS | Speed, Lat, Lon, Elevation, Time UTC, Ambient | 720-726 |

## Freshness Colors

| Age | Color | Meaning |
|-----|-------|---------|
| < 2s | Green | Fresh — signal actively updating |
| 2-5s | Yellow | Aging — source may be slowing |
| 5-10s | Orange | Stale — likely lost |
| 10-30s | Red | Dead — source not responding |
| > 30s | Gray | Never received |

## BLE GATT Design (for future ESP32 firmware)

The body controller ESP32 will act as a BLE peripheral, relaying CAN frames to connected phones.

- **Service UUID**: `4d474200-4247-4d00-0000-000000000001`
- **CAN Relay Characteristic** (Notify): `4d474200-4247-4d00-0000-000000000002`
  - 12 bytes per notification: `uint32_LE arb_id` + `8 bytes data`
  - Body controller relays both received and transmitted CAN frames
  - ~60-80 frames/sec, within BLE 5.0 throughput (~250 KB/s)

The phone app subscribes to notifications and decodes each frame identically to the primary display's CAN source.
