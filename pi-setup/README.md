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

> **WiFi note:** Raspberry Pi Imager only supports one network. Additional networks
> (phone hotspot, workshop, etc.) are added automatically by `base.sh` — see
> [WiFi Networks](#wifi-networks) below.

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

## Step 4 — WiFi Networks

Before running setup, configure your WiFi credentials:

```bash
cd ~/mgb-dash-2026/pi-setup
cp wifi-networks.example.conf wifi-networks.conf
nano wifi-networks.conf
```

Edit `wifi-networks.conf` with your networks (one per line: `SSID,PASSWORD,PRIORITY`).
Higher priority networks are tried first. The file is gitignored so credentials stay local.

## Step 5 — Run Base Setup

Common to **all** Pis. Installs packages, uv, CAN bus, user groups, swap, RTC,
WiFi networks, and the auto-update timer.

```bash
sudo bash ~/mgb-dash-2026/pi-setup/base.sh
```

## Step 6 — Run Role-Specific Setup

Pick one based on which Pi you're building:

**GPS Display** (Pi 3B + Waveshare 1.28" LCD + NEO-6M GPS):
```bash
sudo bash ~/mgb-dash-2026/pi-setup/gps-display.sh
```
> The script will ask about serial port login — answer **No**. This disables the
> login console on the UART so GPSD can use it for GPS data. It does not affect SSH.

**Primary Display** (Pi 4B + Waveshare 3.4" DSI LCD):
```bash
sudo bash ~/mgb-dash-2026/pi-setup/primary-display.sh
```

**Test Monitor** (any Pi, CAN bus diagnostics):
```bash
sudo bash ~/mgb-dash-2026/pi-setup/test-monitor.sh
```

## Step 7 — Reboot

```bash
sudo reboot
```

After reboot:
- CAN bus (`can0`) comes up automatically at 500 kbps
- GPS display / primary display starts automatically via systemd
- Auto-update timer checks for new code every 5 minutes
- RTC keeps time across power cycles

### Post-Reboot Verification — GPS Display

```bash
# SSH back in
ssh pi@gps.local

# GPSD socket listening?
systemctl status gpsd.socket

# GPS display service enabled and running?
systemctl status mgb-gps-display

# CAN bus (only active when USB adapter is plugged in)
ip link show can0

# GPS data stream (once NEO-6M is connected)
gpsmon
```

### Post-Reboot Verification — Primary Display

```bash
ssh pi@primary.local
systemctl status mgb-primary-display
ip link show can0
```

---

## Deploying Code Updates

There are two ways to push code to the Pis:

### Option A — PowerShell Deploy Script (immediate)

From your Windows dev machine, after committing and pushing to GitHub:

```powershell
# Deploy to a specific Pi
.\deploy.ps1 gps
.\deploy.ps1 primary
.\deploy.ps1 testmon

# Deploy to all Pis at once
.\deploy.ps1 all

# Check status of all Pis (commit, service, uptime, temp)
.\deploy.ps1 status
```

The script SSHes into each Pi, runs `git pull`, and restarts the service.
Pis that are offline are skipped with a message.

> **Tip:** Edit the `$Pis` hashtable at the top of `deploy.ps1` if your
> hostnames differ from the defaults (`gps.local`, `primary.local`, `testmon.local`).

### Option B — Auto-Update Timer (background)

Every Pi runs an `mgb-update.timer` that:
1. Fires every 5 minutes (with 30s jitter)
2. Runs `git pull --ff-only`
3. If code changed, restarts the active MGB service
4. If offline or nothing changed, does nothing (silent)

This is installed by `base.sh` and requires no action. It means that when you
enable WiFi/internet on the car, Pis will self-update within 5 minutes.

```bash
# Check timer status on a Pi
systemctl status mgb-update.timer

# View update log
journalctl -t mgb-update

# Trigger an immediate update
sudo systemctl start mgb-update.service

# Disable auto-updates on a specific Pi
sudo systemctl disable mgb-update.timer
```

---

## WiFi Networks

Pis can connect to multiple WiFi networks with priority ordering.
This is useful for:
- **Workshop WiFi** (priority 100) — primary development network
- **Phone hotspot** (priority 50) — field updates at a car show

### Setup

1. Copy the template: `cp wifi-networks.example.conf wifi-networks.conf`
2. Edit with your credentials:
   ```
   HomeWorkshop,YourPasswordHere,100
   PhoneHotspot,HotspotPassword,50
   ```
3. Run `base.sh` (or re-run it to update networks)

The conf file is gitignored. Networks are configured via NetworkManager (`nmcli`)
with `autoconnect` enabled and priority ordering.

### Adding a network later

SSH into the Pi and add directly:
```bash
sudo nmcli connection add type wifi con-name "NewNetwork" \
    ssid "NewNetwork" wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "password" connection.autoconnect yes \
    connection.autoconnect-priority 75
```

---

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

# Auto-update timer
systemctl status mgb-update.timer
journalctl -t mgb-update

# WiFi networks
nmcli connection show

# RTC
sudo hwclock -r

# I2C devices (RTC should appear at 0x68)
i2cdetect -y 1
```

---

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

---

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
9. WiFi networks from `wifi-networks.conf`
10. Auto-update timer (`mgb-update.timer` every 5 min)

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
