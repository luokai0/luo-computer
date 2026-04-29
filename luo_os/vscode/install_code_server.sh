#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# LuoOS — code-server (VS Code) Installer
# Installs the latest code-server and configures it for LuoOS
# ═══════════════════════════════════════════════════════════════════════

set -e

LUO_WORKSPACE="$HOME/luo_workspace"
CODE_SERVER_PORT=8080
CODE_SERVER_PASSWORD="luoos2024"
CODE_SERVER_CONFIG="$HOME/.config/code-server/config.yaml"
LOG_FILE="/tmp/code-server-install.log"

echo ""
echo "  ██╗   ██╗███████╗     ██████╗ ██████╗ ██████╗ ███████╗"
echo "  ██║   ██║██╔════╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝"
echo "  ██║   ██║███████╗    ██║     ██║   ██║██║  ██║█████╗"
echo "  ╚██╗ ██╔╝╚════██║    ██║     ██║   ██║██║  ██║██╔══╝"
echo "   ╚████╔╝ ███████║    ╚██████╗╚██████╔╝██████╔╝███████╗"
echo "    ╚═══╝  ╚══════╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝"
echo ""
echo "  Installing VS Code (code-server) for LuoOS..."
echo ""

# ── Step 1: Create workspace ─────────────────────────────────────────
echo "📁 Creating luo_workspace at $LUO_WORKSPACE..."
mkdir -p "$LUO_WORKSPACE"
mkdir -p "$LUO_WORKSPACE/.vscode"

# Write default workspace settings
cat > "$LUO_WORKSPACE/.vscode/settings.json" << 'EOF'
{
  "workbench.colorTheme": "Default Dark Modern",
  "editor.fontFamily": "'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace",
  "editor.fontSize": 14,
  "editor.tabSize": 2,
  "editor.wordWrap": "on",
  "editor.minimap.enabled": true,
  "editor.formatOnSave": true,
  "terminal.integrated.defaultProfile.linux": "bash",
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 1000,
  "workbench.startupEditor": "none",
  "editor.bracketPairColorization.enabled": true,
  "editor.guides.bracketPairs": true,
  "explorer.confirmDelete": false,
  "telemetry.telemetryLevel": "off"
}
EOF

echo "  ✅ Workspace created at $LUO_WORKSPACE"

# ── Step 2: Install code-server ──────────────────────────────────────
echo ""
echo "⬇️  Downloading latest code-server..."

# Check if already installed
if command -v code-server &>/dev/null; then
    CURRENT_VER=$(code-server --version 2>/dev/null | head -1 | awk '{print $1}')
    echo "  ✅ code-server already installed (version $CURRENT_VER)"
else
    # Use official installer
    curl -fsSL https://code-server.dev/install.sh | sh >> "$LOG_FILE" 2>&1
    echo "  ✅ code-server installed"
fi

# ── Step 3: Configure code-server ───────────────────────────────────
echo ""
echo "⚙️  Configuring code-server..."

mkdir -p "$(dirname $CODE_SERVER_CONFIG)"

cat > "$CODE_SERVER_CONFIG" << EOF
bind-addr: 127.0.0.1:${CODE_SERVER_PORT}
auth: password
password: ${CODE_SERVER_PASSWORD}
cert: false
user-data-dir: $HOME/.local/share/code-server
extensions-dir: $HOME/.local/share/code-server/extensions
EOF

echo "  ✅ Config written to $CODE_SERVER_CONFIG"
echo "  📌 Port: $CODE_SERVER_PORT"
echo "  🔑 Password: $CODE_SERVER_PASSWORD"

# ── Step 4: Install essential extensions ────────────────────────────
echo ""
echo "🔌 Installing VS Code extensions..."

EXTENSIONS=(
    "ms-python.python"
    "ms-vscode.js-debug"
    "dbaeumer.vscode-eslint"
    "esbenp.prettier-vscode"
    "formulahendry.code-runner"
    "PKief.material-icon-theme"
    "GitHub.github-vscode-theme"
    "eamodio.gitlens"
    "ms-vscode.vscode-json"
    "redhat.vscode-yaml"
)

for ext in "${EXTENSIONS[@]}"; do
    echo -n "  Installing $ext..."
    code-server --install-extension "$ext" >> "$LOG_FILE" 2>&1 && echo " ✅" || echo " ⚠️ (skipped)"
done

# ── Step 5: Create welcome file ──────────────────────────────────────
cat > "$LUO_WORKSPACE/welcome.py" << 'EOF'
# ═══════════════════════════════════════════════════════════════════
# Welcome to LuoOS VS Code — powered by code-server
# Your workspace: ~/luo_workspace
# ═══════════════════════════════════════════════════════════════════

print("🖥️  Welcome to LuoOS VS Code!")
print("✨ You're running VS Code in the browser via code-server")
print("")
print("Quick start:")
print("  • Files here sync with Luo Files app")
print("  • Terminal: Ctrl+` (backtick)")
print("  • Command Palette: Ctrl+Shift+P")
print("  • Run this file: press ▶ or F5")
print("")

import sys, platform
print(f"Python {sys.version}")
print(f"Platform: {platform.system()} {platform.release()}")
EOF

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ VS Code (code-server) setup complete!"
echo ""
echo "  To start manually:"
echo "    code-server --config $CODE_SERVER_CONFIG $LUO_WORKSPACE"
echo ""
echo "  Access via LuoOS: click 'VS Code' app icon"
echo "  Direct URL: http://localhost:$CODE_SERVER_PORT"
echo "═══════════════════════════════════════════════════════════"
echo ""
