#!/bin/bash
# Luo OS — Systemd Service Installer
# Run with: sudo ./install_services.sh

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  Luo OS — Systemd Service Installer"
echo "═══════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUO_DIR="${LUO_DIR:-$SCRIPT_DIR}"
USER_NAME="${SUDO_USER:-$USER}"
PYTHON="${PYTHON:-$(which python3)}"

echo ""
echo "Configuration:"
echo "  LUO_DIR: $LUO_DIR"
echo "  USER:    $USER_NAME"
echo "  PYTHON:  $PYTHON"
echo ""

# Create directories
mkdir -p "$LUO_DIR/logs"
mkdir -p "/home/$USER_NAME/.luo_os"

# Process service files
for service in luo-agent luo-server luo-voice; do
    src="$SCRIPT_DIR/systemd/${service}.service"
    dst="/etc/systemd/system/${service}.service"

    if [ -f "$src" ]; then
        echo "Processing: ${service}.service"

        # Replace placeholders
        sed -e "s|%USER%|$USER_NAME|g" \
            -e "s|%LUO_DIR%|$LUO_DIR|g" \
            -e "s|%PYTHON%|$PYTHON|g" \
            "$src" > "$dst"

        echo "  → Installed to: $dst"
    else
        echo "  ✗ Not found: $src"
    fi
done

# Reload systemd
echo ""
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services (but don't start yet)
echo ""
echo "Enabling services..."
for service in luo-agent luo-server; do
    systemctl enable "$service" 2>/dev/null && echo "  ✓ Enabled: $service" || echo "  ✗ Failed: $service"
done

# Optional: enable voice service
read -p "Enable voice service? (requires audio) [y/N]: " enable_voice
if [ "$enable_voice" = "y" ] || [ "$enable_voice" = "Y" ]; then
    systemctl enable luo-voice && echo "  ✓ Enabled: luo-voice"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Installation complete!"
echo ""
echo "  Commands:"
echo "    sudo systemctl start luo-agent    # Start agent service"
echo "    sudo systemctl start luo-server    # Start web server"
echo "    sudo systemctl start luo-voice     # Start voice service"
echo "    sudo systemctl status luo-*        # Check status"
echo "    sudo journalctl -u luo-agent -f    # View logs"
echo ""
echo "  Manual start:"
echo "    cd $LUO_DIR"
echo "    python3 luo_cli.py chat"
echo "═══════════════════════════════════════════════════════════════"