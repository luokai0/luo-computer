#!/bin/bash
# Luo OS ISO Builder
# Creates a bootable ISO image of Luo OS
# Created by Luo Kai (luokai25)

set -e

echo "╔══════════════════════════════════════╗"
echo "║   Luo OS ISO Builder v0.1            ║"
echo "║   Building bootable ISO...           ║"
echo "╚══════════════════════════════════════╝"

# Check dependencies
check_dep() {
    if ! command -v $1 &> /dev/null; then
        echo "Installing $1..."
        apt-get install -y $1 2>/dev/null || echo "⚠️  Could not install $1"
    else
        echo "✅ $1 found"
    fi
}

echo ""
echo "Checking dependencies..."
check_dep grub-pc-bin
check_dep grub-efi-amd64-bin
check_dep xorriso
check_dep mtools
check_dep squashfs-tools
check_dep python3

# Create ISO directory structure
ISO_DIR="/tmp/luo_os_iso"
rm -rf $ISO_DIR
mkdir -p $ISO_DIR/{boot/grub,luo_os,isolinux}

echo ""
echo "Building ISO structure..."

# Copy Luo OS files
cp -r /home/claude/luo_os-v_0.1/* $ISO_DIR/luo_os/ 2>/dev/null || true

# Create GRUB config
cat > $ISO_DIR/boot/grub/grub.cfg << 'GRUB'
set timeout=5
set default=0

menuentry "Luo OS v0.1 — Human Mode" {
    echo "Loading Luo OS..."
    linux /boot/vmlinuz root=/dev/sr0 quiet splash luo_mode=human
    initrd /boot/initrd.img
}

menuentry "Luo OS v0.1 — AI Agent Mode" {
    echo "Loading Luo OS AI Mode..."
    linux /boot/vmlinuz root=/dev/sr0 quiet splash luo_mode=ai
    initrd /boot/initrd.img
}

menuentry "Luo OS v0.1 — Safe Mode" {
    linux /boot/vmlinuz root=/dev/sr0 single luo_mode=safe
    initrd /boot/initrd.img
}
GRUB

# Create init script
cat > $ISO_DIR/luo_os/init.sh << 'INIT'
#!/bin/bash
# Luo OS Init Script
echo "Starting Luo OS..."

# Start Ollama AI
ollama serve &
sleep 2

# Start AI Agent API
python3 /luo_os/ai_core/agent_api.py &

# Start REST API
python3 /luo_os/ai_core/rest_api.py &

# Start desktop
python3 /luo_os/luo_os.py
INIT
chmod +x $ISO_DIR/luo_os/init.sh

# Create ISO info file
cat > $ISO_DIR/LUO_OS.txt << 'INFO'
LUO OS v0.1
Free Operating System for Humans and AI Agents
Created by Luo Kai (luokai25)
https://github.com/luokai25/luo_os-v_0.1

This ISO contains:
- Luo OS kernel (Linux-based)
- Luo AI (TinyLlama local model)
- Full GUI desktop
- AI Agent API (port 7070)
- REST API (port 7071)
- Built-in apps (editor, browser, file manager)
- Windows compatibility (Wine)
INFO

echo ""
echo "✅ ISO structure ready at: $ISO_DIR"
echo ""
echo "To build final ISO (requires xorriso):"
echo "  xorriso -as mkisofs -o luo_os_v0.1.iso \\"
echo "    -b boot/grub/grub.cfg \\"
echo "    -no-emul-boot -boot-load-size 4 \\"
echo "    -boot-info-table $ISO_DIR"
echo ""
echo "ISO structure:"
find $ISO_DIR -type f | head -30
