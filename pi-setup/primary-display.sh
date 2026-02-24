#!/bin/bash
# MGB Dash 2026 — Primary Display Pi Setup
# Pi 4B + Waveshare 3.4" Round DSI LCD (800x800)
# Requires 64-bit Raspberry Pi OS for PySide6
#
# Prerequisites: Run base.sh first
# Usage: sudo bash primary-display.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Primary Display Pi Setup ==="

# Verify 64-bit OS
echo "[1/5] Verifying 64-bit OS..."
if [ "$(uname -m)" != "aarch64" ]; then
    echo "ERROR: 64-bit Raspberry Pi OS required for PySide6."
    echo "Flash a 64-bit image and re-run."
    exit 1
fi

# Install Qt/PySide6 dependencies
echo "[2/5] Installing PySide6 and Qt dependencies..."
apt-get install -y \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    libxkbcommon-dev \
    libfontconfig1-dev \
    libdbus-1-dev
# Install Python dependencies via uv
cd /home/pi/mgb-dash-2026/python/primary-display
uv sync

echo "[3/5] Python dependencies installed via uv sync"

# Configure Innomaker USB2CAN
echo "[4/5] Configuring USB2CAN (gs_usb)..."
modprobe gs_usb
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

# Waveshare 3.4" Round DSI LCD setup
echo "[5/5] Waveshare 3.4\" Round DSI LCD setup..."
# TODO: Install Waveshare DSI display drivers
# TODO: Configure eglfs for direct rendering (no X11)
# TODO: Set up auto-start of dashboard application
echo "  NOTE: Waveshare DSI driver install is model-specific."
echo "  Follow Waveshare wiki for 3.4\" Round DSI LCD."

echo "=== Primary display setup complete ==="
echo "Reboot required for display and CAN changes."
