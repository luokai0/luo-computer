# Luo OS Drivers
*Hardware support layer — based on Linux kernel drivers*

## Included Driver Categories

### Display
- Intel GPU (i915)
- AMD GPU (amdgpu)
- NVIDIA (nouveau open source)
- Virtual display (virtio-gpu)

### Input
- USB HID (keyboard, mouse)
- PS/2 keyboard and mouse
- Touchscreen support
- Gamepad/controller

### Storage
- SATA/AHCI
- NVMe SSD
- USB storage
- SD card reader

### Network
- Intel Ethernet (e1000e)
- Realtek Ethernet (r8169)
- WiFi (iwlwifi, ath9k, rtl8xxxu)
- Bluetooth

### Audio
- Intel HDA
- USB audio
- HDMI audio

### AI Hardware (future)
- NVIDIA CUDA support
- AMD ROCm support
- Intel NPU support
- Dedicated AI chip drivers

## Source
All drivers inherited from Linux kernel v7.0
Reference: https://github.com/torvalds/linux/tree/master/drivers
