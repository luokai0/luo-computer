# Luo OS Bootloader
*GRUB2-based bootloader*

## Boot Sequence
1. BIOS/UEFI → GRUB2
2. GRUB2 → Luo OS kernel
3. Kernel → init system
4. Init → Luo AI daemon starts
5. Luo AI daemon → Desktop GUI launches
6. Desktop ready for human or AI agent use

## Boot Menu Options
- Luo OS v0.1 (default)
- Luo OS v0.1 (AI agent mode)
- Luo OS v0.1 (safe mode)
- Recovery shell
