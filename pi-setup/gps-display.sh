#!/bin/bash
# MGB Dash 2026 — GPS Display Pi Setup
# Pi 3B + Waveshare 1.28" Round LCD (GC9A01 240x240) + NEO-6M GPS
#
# Hardware:
#   LCD:  Waveshare 1.28" GC9A01, 240x240, RGB565, SPI0 @ 40 MHz
#         GPIO: DC=25, RST=27, BL=18 (PWM 1kHz), SPI0 (MOSI=10, SCK=11, CS=8)
#         Driver bundled in gps-display/lib/ (lcdconfig.py + LCD_1inch28.py)
#   GPS:  NEO-6M on UART (GPIO14 TXD0, GPIO15 RXD0) at 9600 baud → gpsd daemon
#   CAN:  Innomaker USB2CAN (gs_usb driver) → SocketCAN can0
#
# Prerequisites: Run base.sh first
# Usage: sudo bash gps-display.sh

set -euo pipefail

echo "=== MGB Dash 2026 — GPS Display Pi Setup ==="

# Install system packages for LCD driver + GPS
echo "[1/5] Installing system packages..."
apt-get install -y \
    gpsd \
    gpsd-clients \
    python3-numpy \
    python3-spidev \
    python3-rpi-gpio

# Install Python dependencies via uv
echo "[2/5] Installing Python dependencies..."
cd /home/pi/mgb-dash-2026/gps-display
uv sync

# Enable SPI for GC9A01 display
echo "[3/5] Enabling SPI interface..."
raspi-config nonint do_spi 0

# Enable UART for GPS receiver and configure gpsd
echo "[4/5] Configuring UART + gpsd for GPS..."
# Disable serial console, enable UART hardware
raspi-config nonint do_serial 1    # disable console
raspi-config nonint do_serial_hw 1 # enable hardware UART
# Add to config.txt if not already present
if ! grep -q "enable_uart=1" /boot/firmware/config.txt; then
    echo "enable_uart=1" >> /boot/firmware/config.txt
fi

# Configure gpsd to listen on UART (NEO-6M at 9600 baud on /dev/ttyAMA0)
cat > /etc/default/gpsd <<'EOF'
# MGB Dash 2026 — gpsd configuration for NEO-6M GPS
START_DAEMON="true"
GPSD_OPTIONS="-n"
DEVICES="/dev/ttyAMA0"
USBAUTO="false"
GPSD_SOCKET="/var/run/gpsd.sock"
EOF

# Enable gpsd socket activation
systemctl enable gpsd.socket
systemctl start gpsd.socket

# Configure Innomaker USB2CAN
echo "[5/5] Configuring USB2CAN (gs_usb)..."
modprobe gs_usb
# Create systemd service to bring up can0 at boot
cat > /etc/systemd/system/can0.service <<'EOF'
[Unit]
Description=Bring up CAN0 interface
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ip link set can0 type can bitrate 500000
ExecStartPost=/sbin/ip link set can0 up
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl enable can0.service

echo "=== GPS display setup complete ==="
echo "Reboot required for UART, SPI, and CAN changes."
