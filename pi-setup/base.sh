#!/bin/bash
# MGB Dash 2026 — Pi Base Setup
# Common setup for all Raspberry Pis (run first, then role-specific script)
#
# Configures:
#   - System packages (git, python3, can-utils, etc.)
#   - uv package manager
#   - SocketCAN kernel modules
#   - Innomaker USB2CAN V3.3 (gs_usb) → SocketCAN can0 at 500 kbps
#   - User group membership for hardware access (dialout, spi, i2c, gpio)
#   - 2 GB swap for stability on low-RAM Pis (Pi 3B = 1 GB)
#   - PCF8523 I2C real-time clock
#
# Configuration verified against running prototype pi3-a.local
#
# Usage: sudo bash base.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Base Pi Setup ==="

# Update system
echo "[1/9] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install core tools
echo "[2/9] Installing core tools..."
apt-get install -y \
    git \
    python3-pip \
    python3-venv \
    python3-dev \
    can-utils \
    iproute2 \
    net-tools \
    vim \
    htop \
    i2c-tools \
    dphys-swapfile

# Ensure pi user has hardware access groups
echo "[3/9] Configuring user groups for hardware access..."
for grp in dialout spi i2c gpio; do
    usermod -aG "$grp" pi 2>/dev/null || true
done

# Configure 2 GB swap for stability (Pi 3B has only 1 GB RAM)
echo "[4/9] Configuring swap..."
if [ -f /etc/dphys-swapfile ]; then
    sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
    systemctl restart dphys-swapfile
fi

# Install uv package manager
echo "[5/9] Installing uv package manager..."
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

# Enable SocketCAN kernel modules
echo "[6/9] Configuring SocketCAN..."
modprobe can
modprobe can_raw
modprobe can_dev
modprobe gs_usb

# Ensure CAN modules load at boot (idempotent — won't duplicate)
for mod in can can_raw can_dev; do
    if ! grep -q "^${mod}$" /etc/modules 2>/dev/null; then
        echo "$mod" >> /etc/modules
    fi
done

# Configure Innomaker USB2CAN V3.3 (gs_usb) → can0 at 500 kbps
# Uses /etc/network/interfaces drop-in — matches proven prototype pi3-a.local
echo "[7/9] Configuring USB2CAN (can0 at 500 kbps)..."
cat > /etc/network/interfaces.d/can0 <<'EOF'
# Innomaker USB2CAN V3.3 (gs_usb) — 500 kbps
# Matches prototype pi3-a.local configuration
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 down
    pre-up /sbin/ip link set can0 txqueuelen 1000 type can bitrate 500000
    up /sbin/ifconfig can0 up
    down /sbin/ifconfig can0 down
EOF

# Ensure /etc/network/interfaces sources the drop-in directory
if ! grep -q "source /etc/network/interfaces.d/" /etc/network/interfaces 2>/dev/null; then
    echo "source /etc/network/interfaces.d/*" >> /etc/network/interfaces
fi

# Remove any old can0.service if present (we use /etc/network/interfaces now)
if [ -f /etc/systemd/system/can0.service ]; then
    systemctl disable can0.service 2>/dev/null || true
    rm -f /etc/systemd/system/can0.service
    systemctl daemon-reload
fi

# Configure PCF8523 I2C real-time clock
# Keeps time across reboots when no network/GPS is available
echo "[8/9] Configuring I2C RTC (PCF8523)..."
CONFIG_TXT="/boot/firmware/config.txt"
[ -f "$CONFIG_TXT" ] || CONFIG_TXT="/boot/config.txt"
if ! grep -q "dtoverlay=i2c-rtc,pcf8523" "$CONFIG_TXT" 2>/dev/null; then
    echo "dtoverlay=i2c-rtc,pcf8523" >> "$CONFIG_TXT"
fi
if ! grep -q "dtparam=i2c_arm=on" "$CONFIG_TXT" 2>/dev/null; then
    echo "dtparam=i2c_arm=on" >> "$CONFIG_TXT"
fi
# Ensure i2c-dev module loads at boot
if ! grep -q "^i2c-dev$" /etc/modules 2>/dev/null; then
    echo "i2c-dev" >> /etc/modules
fi

# Clone or update the monorepo
echo "[9/9] Setting up project directory..."
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
echo "Reboot recommended after first run."
