#!/bin/bash
# MGB Dash 2026 — GPS Display Pi Setup
# Pi 3B + Waveshare 1.28" Round LCD (GC9A01 240x240) + NEO-6M GPS
#
# Hardware:
#   LCD:  Waveshare 1.28" GC9A01, 240x240, RGB565, SPI0 @ 40 MHz
#         GPIO: DC=25, RST=27, BL=18 (PWM 1kHz), SPI0 (MOSI=10, SCK=11, CS=8)
#         Driver bundled in python/gps-display/lib/ (lcdconfig.py + LCD_1inch28.py)
#   GPS:  NEO-6M on PL011 UART (/dev/ttyAMA0 GPIO14/15) at 9600 baud → gpsd daemon
#         Bluetooth is disabled to free PL011 for GPS (more reliable than mini UART)
#   CAN:  Innomaker USB2CAN (gs_usb) → SocketCAN can0 (configured by base.sh)
#
# Configuration verified against running prototype pi3-a.local
#
# Prerequisites: Run base.sh first
# Usage: sudo bash gps-display.sh

set -euo pipefail

echo "=== MGB Dash 2026 — GPS Display Pi Setup ==="

REPO_DIR="/home/pi/mgb-dash-2026"

# Install system packages for LCD driver + GPS
echo "[1/7] Installing system packages..."
apt-get install -y \
    gpsd \
    gpsd-clients \
    gpsd-tools \
    python3-numpy \
    python3-spidev \
    python3-rpi-lgpio

# Install Python dependencies via uv
echo "[2/7] Installing Python dependencies..."
cd "$REPO_DIR/python/gps-display"
uv sync

# Enable SPI for GC9A01 display
echo "[3/7] Enabling SPI interface..."
raspi-config nonint do_spi 0

# Disable Bluetooth to free PL011 UART for GPS
# Pi 3B default: PL011 (/dev/ttyAMA0) → Bluetooth, mini UART (/dev/ttyS0) → GPIO
# With disable-bt: PL011 (/dev/ttyAMA0) → GPIO (better clock, more reliable for GPS)
echo "[4/7] Disabling Bluetooth, configuring UART for GPS..."
CONFIG_TXT="/boot/firmware/config.txt"
[ -f "$CONFIG_TXT" ] || CONFIG_TXT="/boot/config.txt"
if ! grep -q "dtoverlay=disable-bt" "$CONFIG_TXT" 2>/dev/null; then
    echo "dtoverlay=disable-bt" >> "$CONFIG_TXT"
fi
if ! grep -q "enable_uart=1" "$CONFIG_TXT" 2>/dev/null; then
    echo "enable_uart=1" >> "$CONFIG_TXT"
fi
# Disable Bluetooth systemd services
systemctl disable hciuart.service 2>/dev/null || true
systemctl disable bluetooth.service 2>/dev/null || true
# Disable serial console, enable hardware UART
raspi-config nonint do_serial 1    # disable serial console
raspi-config nonint do_serial_hw 1 # enable hardware UART

# Configure gpsd for PL011 UART
# Device: /dev/ttyAMA0 (PL011 — freed from Bluetooth by dtoverlay=disable-bt)
# Options: -n (poll immediately), -G (allow remote connections for monitoring)
echo "[5/7] Configuring gpsd..."
cat > /etc/default/gpsd <<'EOF'
# MGB Dash 2026 — gpsd configuration for NEO-6M GPS
# PL011 UART on GPIO14/15 (Bluetooth disabled to free this UART)
DEVICES="/dev/ttyAMA0"
START_DAEMON="true"
GPSD_OPTIONS="-n -G"
GPSD_SOCKET="/var/run/gpsd.socket"
USBAUTO="true"
EOF

echo "[6/7] Enabling gpsd remote access..."
# Enable gpsd remote access on port 2947 (all interfaces)
# Override default gpsd.socket to listen on 0.0.0.0:2947 and [::]:2947
mkdir -p /etc/systemd/system/gpsd.socket.d
cat > /etc/systemd/system/gpsd.socket.d/remote-access.conf <<'EOF'
# Allow remote gpsd connections for CAN bus monitoring tools
[Socket]
# Clear inherited ListenStream values, then redefine
ListenStream=
ListenStream=/run/gpsd.sock
ListenStream=[::]:2947
ListenStream=0.0.0.0:2947
SocketMode=0600
BindIPv6Only=ipv6-only
EOF

systemctl daemon-reload
systemctl enable gpsd.socket
systemctl restart gpsd.socket

# Create systemd service for GPS display application
echo "[7/7] Creating systemd service for GPS display..."
cat > /etc/systemd/system/mgb-gps-display.service <<EOF
[Unit]
Description=MGB Dash — GPS Display (LCD + CAN writer)
After=network.target gpsd.socket
Wants=gpsd.socket

[Service]
WorkingDirectory=$REPO_DIR/python/gps-display
ExecStart=$REPO_DIR/python/gps-display/.venv/bin/python -u main.py
Restart=always
RestartSec=120
StandardOutput=journal
StandardError=journal
User=pi

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable mgb-gps-display.service

echo "=== GPS display setup complete ==="
echo "Reboot required for UART, SPI, and CAN changes."
echo "After reboot, the GPS display will start automatically."
