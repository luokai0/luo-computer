#include "shell.h"
#include "serial.h"
#include "commands.h"

void shell_run(void) {
    char buf[256];

    commands_init();

    serial_print("  luo_os v1.0 — ");
    serial_print_int(commands_count());
    serial_println(" commands loaded");
    serial_println("  Type 'help' to see all commands");
    serial_println("  Type 'ai <question>' for AI assistance");
    serial_println("  Type 'ollama run llama3.2' to start local AI");
    serial_println("");

    while (1) {
        serial_print("luo_os:~$ ");
        serial_readline(buf, 256);
        if (!buf[0]) continue;
        commands_run(buf);
    }
}
