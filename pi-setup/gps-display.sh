#!/bin/bash
# MGB Dash 2026 — GPS Display Pi Setup
# Pi 3B + Waveshare 2" Round LCD + NEO-6M GPS
#
# Prerequisites: Run base.sh first
# Usage: sudo bash gps-display.sh

set -euo pipefail

echo "=== MGB Dash 2026 — GPS Display Pi Setup ==="

# Install GPS Pi dependencies
echo "[1/4] Installing GPS display dependencies..."
pip3 install \
    pyserial \
    ephem \
    Pillow \
    --break-system-packages

# Enable UART for GPS receiver
echo "[2/4] Configuring UART for GPS..."
# Disable serial console, enable UART hardware
raspi-config nonint do_serial 1    # disable console
raspi-config nonint do_serial_hw 1 # enable hardware UART
# Add to config.txt if not already present
if ! grep -q "enable_uart=1" /boot/firmware/config.txt; then
    echo "enable_uart=1" >> /boot/firmware/config.txt
fi

# Configure Innomaker USB2CAN
echo "[3/4] Configuring USB2CAN (gs_usb)..."
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

# Waveshare 2" round LCD setup
echo "[4/4] Waveshare 2\" round LCD setup..."
# TODO: Install Waveshare drivers (depends on exact model — SPI vs DSI)
# TODO: Configure SPI if needed
# TODO: Install display-specific Python library
echo "  NOTE: Waveshare display driver install is model-specific."
echo "  Follow Waveshare wiki for your exact 2\" round LCD variant."

echo "=== GPS display setup complete ==="
echo "Reboot required for UART and CAN changes."
