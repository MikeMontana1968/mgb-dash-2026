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
#   - WiFi networks from wifi-networks.conf (multiple SSIDs with priority)
#   - Auto-update timer (git pull + service restart every 5 minutes)
#
# Configuration verified against running prototype pi3-a.local
#
# Usage: sudo bash base.sh

set -euo pipefail

echo "=== MGB Dash 2026 — Base Pi Setup ==="

# Disable unnecessary services that slow boot
systemctl disable ModemManager.service 2>/dev/null || true
systemctl mask ModemManager.service 2>/dev/null || true

# Update system
echo "[1/11] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install core tools
echo "[2/11] Installing core tools..."
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
echo "[3/11] Configuring user groups for hardware access..."
for grp in dialout spi i2c gpio; do
    usermod -aG "$grp" pi 2>/dev/null || true
done

# Configure 2 GB swap for stability (Pi 3B has only 1 GB RAM)
echo "[4/11] Configuring swap..."
if [ -f /etc/dphys-swapfile ]; then
    sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
    systemctl restart dphys-swapfile
fi

# Install uv package manager
echo "[5/11] Installing uv package manager..."
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

# Enable SocketCAN kernel modules
echo "[6/11] Configuring SocketCAN..."
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
# Uses a systemd service (works on both Bullseye and Bookworm)
# Prototype pi3-a.local used /etc/network/interfaces but Bookworm uses NetworkManager
echo "[7/11] Configuring USB2CAN (can0 at 500 kbps)..."
cat > /etc/systemd/system/can0.service <<'EOF'
[Unit]
Description=Bring up CAN0 interface (Innomaker USB2CAN V3.3, 500 kbps)
After=network.target
ConditionPathExists=/sys/class/net/can0

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/ip link set can0 txqueuelen 1000 type can bitrate 500000
ExecStart=/sbin/ip link set can0 up
ExecStop=/sbin/ip link set can0 down

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable can0.service

# Clean up any old /etc/network/interfaces CAN config
if [ -f /etc/network/interfaces.d/can0 ]; then
    rm -f /etc/network/interfaces.d/can0
fi

# Configure PCF8523 I2C real-time clock
# Keeps time across reboots when no network/GPS is available
echo "[8/11] Configuring I2C RTC (PCF8523)..."
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
echo "[9/11] Setting up project directory..."
REPO_DIR="/home/pi/mgb-dash-2026"
if [ -d "$REPO_DIR" ]; then
    echo "Repo exists, pulling latest..."
    cd "$REPO_DIR" && git pull
else
    echo "Clone the repo manually:"
    echo "  git clone <repo-url> $REPO_DIR"
fi

# Configure additional WiFi networks from wifi-networks.conf
# The primary network is set via Raspberry Pi Imager at flash time.
# This adds extra networks (phone hotspot, workshop, etc.) with priority ordering.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WIFI_CONF="$SCRIPT_DIR/wifi-networks.conf"
echo "[10/11] Configuring WiFi networks..."
if [ -f "$WIFI_CONF" ]; then
    while IFS=, read -r ssid password priority; do
        # Skip comments and blank lines
        [[ "$ssid" =~ ^#.*$ || -z "$ssid" ]] && continue
        ssid=$(echo "$ssid" | xargs)
        password=$(echo "$password" | xargs)
        priority=$(echo "$priority" | xargs)
        # Remove existing connection with this name to allow re-running
        nmcli connection delete "$ssid" 2>/dev/null || true
        nmcli connection add \
            type wifi \
            con-name "$ssid" \
            ssid "$ssid" \
            wifi-sec.key-mgmt wpa-psk \
            wifi-sec.psk "$password" \
            connection.autoconnect yes \
            connection.autoconnect-priority "${priority:-0}"
        echo "  Added WiFi: $ssid (priority $priority)"
    done < "$WIFI_CONF"
else
    echo "  No wifi-networks.conf found — skipping."
    echo "  Copy wifi-networks.example.conf → wifi-networks.conf to add networks."
fi

# Install auto-update timer
# Tries git pull every 5 minutes; restarts service if code changed.
# Fails silently when offline — no harm done.
echo "[11/11] Installing auto-update timer..."
cat > /usr/local/bin/mgb-update.sh <<'SCRIPT'
#!/bin/bash
# MGB Dash 2026 — Auto-update script
# Called by mgb-update.timer every 5 minutes.
# Pulls latest code from GitHub; restarts the active service if code changed.
# Exits silently if offline or if nothing changed.

REPO_DIR="/home/pi/mgb-dash-2026"
cd "$REPO_DIR" || exit 0

OLD_HEAD=$(git rev-parse HEAD 2>/dev/null) || exit 0
git pull --ff-only 2>/dev/null || exit 0
NEW_HEAD=$(git rev-parse HEAD 2>/dev/null) || exit 0

if [ "$OLD_HEAD" != "$NEW_HEAD" ]; then
    logger -t mgb-update "Code updated: $OLD_HEAD → $NEW_HEAD"
    # Restart whichever MGB service is enabled on this Pi
    for svc in mgb-gps-display mgb-primary-display; do
        if systemctl is-enabled "$svc" 2>/dev/null | grep -q enabled; then
            systemctl restart "$svc"
            logger -t mgb-update "Restarted $svc"
        fi
    done
fi
SCRIPT
chmod +x /usr/local/bin/mgb-update.sh

cat > /etc/systemd/system/mgb-update.service <<'EOF'
[Unit]
Description=MGB Dash — Pull latest code and restart if changed
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/mgb-update.sh
User=pi
EOF

cat > /etc/systemd/system/mgb-update.timer <<'EOF'
[Unit]
Description=MGB Dash — Auto-update every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable mgb-update.timer
systemctl start mgb-update.timer

echo "=== Base setup complete ==="
echo "Next: run the role-specific setup script."
echo "Reboot recommended after first run."
