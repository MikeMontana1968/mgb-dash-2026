#!/bin/bash
# MGB Dash 2026 — Test/Monitor Pi Setup
# Dedicated Pi for CAN bus testing and diagnostics
# Innomaker USB2CAN + CLI tools
#
# Prerequisites: Run base.sh first
# Usage: sudo bash test-monitor.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Test/Monitor Pi Setup ==="

REPO_DIR="/home/pi/mgb-dash-2026"
export PATH="/root/.local/bin:/home/pi/.local/bin:$PATH"

# Install Python dependencies for tools
echo "[1/2] Installing Python dependencies..."
cd "$REPO_DIR/python/tools"
uv sync

echo "[2/2] CAN bus configured by base.sh"

echo "=== Test/Monitor setup complete ==="
echo ""
echo "Tools available in $REPO_DIR/python/tools/:"
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
echo "Reboot required if this is the first run."
