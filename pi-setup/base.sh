#!/bin/bash
# MGB Dash 2026 — Pi Base Setup
# Common setup for all Raspberry Pis (run first, then role-specific script)
#
# Usage: sudo bash base.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Base Pi Setup ==="

# Update system
echo "[1/5] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install core tools
echo "[2/5] Installing core tools..."
apt-get install -y \
    git \
    python3-pip \
    python3-venv \
    can-utils \
    iproute2 \
    vim \
    htop

# Install uv package manager
echo "[3/5] Installing uv package manager..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Enable SocketCAN kernel modules
echo "[4/5] Configuring SocketCAN..."
modprobe can
modprobe can_raw
modprobe can_dev

# Ensure modules load at boot
cat >> /etc/modules <<'EOF'
can
can_raw
can_dev
EOF

# Clone or update the monorepo
echo "[5/5] Setting up project directory..."
REPO_DIR="/home/pi/mgb-dash-2026"
if [ -d "$REPO_DIR" ]; then
    echo "Repo exists, pulling latest..."
    cd "$REPO_DIR" && git pull
else
    echo "Clone the repo manually:"
    echo "  git clone <repo-url> $REPO_DIR"
fi

echo "=== Base setup complete ==="
echo "Next: run the role-specific setup script."
