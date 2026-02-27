#!/bin/bash
# MGB Dash 2026 — Primary Display Pi Setup
# Pi 4B + Waveshare 3.4" Round DSI LCD (800x800)
# Uses pycairo + pygame for rendering
#
# Hardware:
#   LCD: Waveshare 3.4" Round DSI LCD, 800x800
#   CAN: Innomaker USB2CAN (gs_usb) → SocketCAN can0 (configured by base.sh)
#
# Prerequisites: Run base.sh first
# Usage: sudo bash primary-display.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Primary Display Pi Setup ==="

REPO_DIR="/home/pi/mgb-dash-2026"
export PATH="/root/.local/bin:/home/pi/.local/bin:$PATH"

# Verify 64-bit OS
echo "[1/6] Verifying 64-bit OS..."
if [ "$(uname -m)" != "aarch64" ]; then
    echo "ERROR: 64-bit Raspberry Pi OS required."
    echo "Flash a 64-bit image and re-run."
    exit 1
fi

# Install system dependencies for pycairo + pygame
echo "[2/6] Installing system dependencies..."
apt-get install -y \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    python3-numpy

# Install Python dependencies via uv (workspace sync from repo root)
echo "[3/6] Installing Python dependencies..."
cd "$REPO_DIR"
uv sync --package mgb-primary-display

# Waveshare 3.4" Round DSI LCD setup
echo "[4/6] Waveshare 3.4\" Round DSI LCD setup..."
# TODO: Install Waveshare DSI display drivers
# TODO: Configure for direct rendering
echo "  NOTE: Waveshare DSI driver install is model-specific."
echo "  Follow Waveshare wiki for 3.4\" Round DSI LCD."

# Sudoers for GPS-based clock sync (passwordless date + timedatectl)
echo "[5/6] Configuring sudoers for clock sync..."
cat > /etc/sudoers.d/mgb-clock-sync <<'SUDOERS'
# Allow pi user to set system clock and timezone from GPS CAN data
pi ALL=(ALL) NOPASSWD: /usr/bin/date
pi ALL=(ALL) NOPASSWD: /usr/bin/timedatectl
SUDOERS
chmod 0440 /etc/sudoers.d/mgb-clock-sync

# Create systemd service for primary display
echo "[6/6] Creating systemd service for primary display..."
cat > /etc/systemd/system/mgb-primary-display.service <<EOF
[Unit]
Description=MGB Dash — Primary Display (pycairo + pygame)
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
WorkingDirectory=$REPO_DIR/python/primary-display
ExecStart=$REPO_DIR/.venv/bin/python -u main.py --source can
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
User=pi

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable mgb-primary-display.service

echo "=== Primary display setup complete ==="
echo "Reboot required for display and CAN changes."
echo "After reboot, the primary display will start automatically."
