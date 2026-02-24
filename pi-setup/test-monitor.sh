#!/bin/bash
# MGB Dash 2026 — Test/Monitor Pi Setup
# Dedicated Pi for CAN bus testing and diagnostics
# Innomaker USB2CAN + CLI tools
#
# Prerequisites: Run base.sh first
# Usage: sudo bash test-monitor.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Test/Monitor Pi Setup ==="

# python-can already installed via base.sh
echo "[1/2] Dependencies already installed via base.sh"

# Configure Innomaker USB2CAN
echo "[2/2] Configuring USB2CAN (gs_usb)..."
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

echo "=== Test/Monitor setup complete ==="
echo ""
echo "Tools available in /home/pi/mgb-dash-2026/python/tools/:"
echo "  python3 can_monitor.py    — Decoded CAN traffic viewer"
echo "  python3 can_emulate.py    — Module emulator"
echo "  python3 can_inject.py     — Send single CAN frames"
echo "  python3 can_replay.py     — Record/playback CAN sessions"
echo "  python3 can_stress.py     — Bus load testing"
echo "  python3 can_cell_query.py — Battery cell voltage query"
echo "  python3 can_scan.py       — Bus discovery / module detection"
echo ""
echo "Quick CAN commands:"
echo "  candump can0              — Raw CAN traffic"
echo "  cansend can0 700#4655454C200A0000  — Send a frame"
echo ""
echo "Reboot required for CAN changes."
