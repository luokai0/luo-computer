#!/bin/bash
set -e

echo "=== luo_os Sandbox v1.0 ==="
echo "Starting all services..."

# pull default AI model if not present
if ! ollama list 2>/dev/null | grep -q llama3.2; then
    echo "[ollama] pulling llama3.2 (first run — may take a few minutes)..."
    ollama pull llama3.2 &
fi

echo "[qemu]   luo_os kernel starting..."
echo "[novnc]  desktop at http://localhost:6080/vnc.html"
echo "[ollama] AI at http://localhost:11434"
echo "[agent]  AI agent connecting to OS..."
echo ""
echo "Open in browser: http://localhost:6080/vnc.html"
echo "Then click Connect to see the luo_os desktop"
echo ""

# start all services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/luoos.conf
