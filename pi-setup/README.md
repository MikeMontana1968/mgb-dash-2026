# Pi Setup — Quick Start

## Overview

Each Raspberry Pi in the dashboard runs **Raspberry Pi OS Lite (64-bit)** — no desktop
environment. Applications run as systemd services and render directly to their display
hardware (SPI for GPS, DSI for primary display).

## What You Need

- Raspberry Pi Imager ([download](https://www.raspberrypi.com/software/))
- microSD card (16 GB+)
- WiFi credentials for initial setup
- SSH public key (`~/.ssh/omnibook.pub`)

## Step 1 — Flash the SD Card

1. Open **Raspberry Pi Imager**
2. Choose OS → **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (64-bit)**
3. Choose your microSD card
4. Click the **gear icon** (or Ctrl+Shift+X) to open advanced settings:

| Setting          | GPS Display     | Primary Display  | Test Monitor     |
|------------------|-----------------|------------------|------------------|
| Hostname         | `gps`           | `primary`        | `testmon`        |
| Enable SSH       | Public key auth | Public key auth  | Public key auth  |
| Username         | `pi`            | `pi`             | `pi`             |
| WiFi             | Your network    | Your network     | Your network     |
| Locale           | `America/New_York` | `America/New_York` | `America/New_York` |

5. Write the image

## Step 2 — First Boot

Insert the SD card, power on, and wait ~90 seconds for first boot to complete.

```powershell
# Verify the Pi is reachable (substitute hostname from table above)
ssh pi@gps.local
```

## Step 3 — Clone the Repo

```bash
git clone https://github.com/MikeMontana1968/mgb-dash-2026.git ~/mgb-dash-2026
```

## Step 4 — Run Base Setup

Common to **all** Pis. Installs packages, uv, CAN bus, user groups, swap, RTC.

```bash
sudo bash ~/mgb-dash-2026/pi-setup/base.sh
```

## Step 5 — Run Role-Specific Setup

Pick one based on which Pi you're building:

**GPS Display** (Pi 3B + Waveshare 1.28" LCD + NEO-6M GPS):
```bash
sudo bash ~/mgb-dash-2026/pi-setup/gps-display.sh
```

**Primary Display** (Pi 4B + Waveshare 3.4" DSI LCD):
```bash
sudo bash ~/mgb-dash-2026/pi-setup/primary-display.sh
```

**Test Monitor** (any Pi, CAN bus diagnostics):
```bash
sudo bash ~/mgb-dash-2026/pi-setup/test-monitor.sh
```

## Step 6 — Reboot

```bash
sudo reboot
```

After reboot:
- CAN bus (`can0`) comes up automatically at 500 kbps
- GPS display / primary display starts automatically via systemd
- RTC keeps time across power cycles

## Verifying the Setup

```bash
# CAN bus is up
ip link show can0

# CAN traffic (if bus is active)
candump can0

# GPS fix (GPS display Pi only)
gpsmon

# Application status
systemctl status mgb-gps-display          # GPS display Pi
systemctl status mgb-primary-display      # Primary display Pi

# Application logs
journalctl -u mgb-gps-display -f          # GPS display Pi
journalctl -u mgb-primary-display -f      # Primary display Pi

# RTC
sudo hwclock -r

# I2C devices (RTC should appear at 0x68)
i2cdetect -y 1
```

## Hardware Reference

### Innomaker USB2CAN V3.3

All Pis use the same USB-to-CAN adapter.

- USB ID: `1d50:606f`
- Driver: `gs_usb` (loaded automatically)
- Interface: `can0` at 500 kbps, txqueuelen 1000
- Config: `/etc/network/interfaces.d/can0`

### GPS (Pi 3B only)

- NEO-6M on PL011 UART (`/dev/ttyAMA0`, GPIO14/15)
- Bluetooth is disabled (`dtoverlay=disable-bt`) to free PL011 for GPS
- gpsd listens on port 2947 (all interfaces) for remote monitoring

### PCF8523 RTC (all Pis)

- I2C address: `0x68`
- Overlay: `dtoverlay=i2c-rtc,pcf8523`
- Keeps time when no network or GPS is available

## Updating

To pull the latest code and restart services:

```bash
cd ~/mgb-dash-2026 && git pull

# Restart whichever service this Pi runs:
sudo systemctl restart mgb-gps-display
# or
sudo systemctl restart mgb-primary-display
```

## What Each Script Does

### base.sh (all Pis)
1. System update + core packages (git, python3, can-utils, i2c-tools, etc.)
2. User groups for hardware access (dialout, spi, i2c, gpio)
3. 2 GB swap (critical for Pi 3B's 1 GB RAM)
4. uv package manager
5. SocketCAN kernel modules + gs_usb
6. CAN bus interface (`/etc/network/interfaces.d/can0`)
7. PCF8523 I2C RTC
8. Clone/update monorepo

### gps-display.sh
1. gpsd + LCD/SPI packages
2. Python dependencies (uv sync)
3. SPI enabled for GC9A01 display
4. Bluetooth disabled, PL011 UART freed for GPS
5. gpsd configured (`/dev/ttyAMA0`, remote access on port 2947)
6. gpsd.socket override for remote monitoring
7. `mgb-gps-display.service` — autostart on boot

### primary-display.sh
1. 64-bit OS verification
2. pycairo + pygame + SDL2 system dependencies
3. Python dependencies (uv sync)
4. Waveshare 3.4" DSI LCD setup (manual step — see Waveshare wiki)
5. `mgb-primary-display.service` — autostart on boot

### test-monitor.sh
1. Python dependencies for CLI tools (uv sync)
2. CAN bus ready via base.sh
