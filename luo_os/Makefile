CC      = gcc
CFLAGS  = -m32 -ffreestanding -O2 -Wall -Wextra -fno-stack-protector -fno-pic -Ikernel
LDFLAGS = -m elf_i386 -T linker.ld

GRUB_CFG = isodir/boot/grub/grub.cfg
ISO      = luo_os.iso

BOOT_OBJS = boot/boot.o boot/isr.o boot/context_switch.o
KERN_OBJS = kernel/serial.o kernel/idt.o kernel/timer.o kernel/keyboard.o \
            kernel/memory.o kernel/fs.o kernel/process.o \
            kernel/commands.o kernel/shell.o kernel/kernel.o

all: $(ISO)

boot/%.o: boot/%.asm
	nasm -f elf32 $< -o $@

kernel/%.o: kernel/%.c
	$(CC) $(CFLAGS) -c $< -o $@

kernel.bin: $(BOOT_OBJS) $(KERN_OBJS)
	ld $(LDFLAGS) -o $@ $^

$(GRUB_CFG):
	@mkdir -p isodir/boot/grub
	@printf 'set timeout=0\nset default=0\nmenuentry "luo_os" {\n    multiboot /boot/kernel.bin\n    boot\n}\n' > $(GRUB_CFG)

$(ISO): kernel.bin $(GRUB_CFG)
	cp kernel.bin isodir/boot/kernel.bin
	grub-mkrescue -o $(ISO) isodir 2>/dev/null

run: $(ISO)
	qemu-system-i386 -cdrom $(ISO) -serial stdio \
	    -display none -m 64M -no-reboot -no-shutdown

clean:
	rm -f boot/*.o kernel/*.o kernel.bin $(ISO)
	rm -rf isodir
