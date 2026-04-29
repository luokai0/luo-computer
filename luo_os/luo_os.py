#!/usr/bin/env python3
"""
Luo OS v0.1 — Main Launcher
The OS that is free for all — humans and AI agents
Created by Luo Kai (luokai25)
"""

import tkinter as tk
import threading
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

class LuoOSBoot:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Luo OS v0.1 — Booting...")
        self.root.configure(bg="#0a0a1a")
        self.root.geometry("800x520")
        self.root.resizable(False, False)
        self.boot_steps = [
            ("Initializing Luo OS kernel...",     0.4),
            ("Loading hardware drivers...",        0.4),
            ("Starting AI Core daemon...",         0.6),
            ("Loading memory system...",           0.3),
            ("Mounting filesystems...",            0.3),
            ("Starting Agent API (port 7070)...",  0.4),
            ("Starting REST API (port 7071)...",   0.4),
            ("Loading Windows compatibility...",   0.3),
            ("Starting shell environment...",      0.3),
            ("Launching desktop GUI...",           0.4),
            ("Luo OS ready.",                      0.2),
        ]
        self.setup_boot_screen()

    def setup_boot_screen(self):
        tk.Label(self.root, text="⚡ LUO OS", font=("Courier", 56, "bold"),
                fg="#00ffcc", bg="#0a0a1a").pack(pady=25)
        tk.Label(self.root, text="Free OS for Humans & AI Agents — v0.1",
                font=("Courier", 12), fg="#ffffff", bg="#0a0a1a").pack()
        tk.Label(self.root, text="by Luo Kai (luokai25)",
                font=("Courier", 10), fg="#333355", bg="#0a0a1a").pack(pady=3)

        self.progress_canvas = tk.Canvas(self.root, height=6, bg="#111133",
                                          highlightthickness=0, width=600)
        self.progress_canvas.pack(pady=15)
        self.progress_fill = self.progress_canvas.create_rectangle(0, 0, 0, 6, fill="#00ffcc", outline="")

        self.log = tk.Label(self.root, text="Starting Luo OS...",
                           font=("Courier", 11), fg="#00ffcc", bg="#0a0a1a")
        self.log.pack(pady=8)

        mode_frame = tk.Frame(self.root, bg="#0a0a1a")
        mode_frame.pack(pady=10)
        tk.Label(mode_frame, text="Boot Mode:", font=("Courier", 11),
                fg="#ffffff", bg="#0a0a1a").pack(side="left", padx=10)
        self.mode = tk.StringVar(value="human")
        for text, val in [("Human Mode", "human"), ("AI Agent Mode", "ai"), ("Safe Mode", "safe")]:
            tk.Radiobutton(mode_frame, text=text, variable=self.mode, value=val,
                          font=("Courier", 11), fg="#00ffcc", bg="#0a0a1a",
                          selectcolor="#111133", activebackground="#0a0a1a").pack(side="left", padx=8)

        tk.Button(self.root, text="⚡  BOOT LUO OS",
                 font=("Courier", 14, "bold"), bg="#00ffcc", fg="#0a0a1a",
                 relief="flat", width=22, command=self.start_boot).pack(pady=15)

    def start_boot(self):
        t = threading.Thread(target=self.boot_sequence)
        t.daemon = True
        t.start()

    def boot_sequence(self):
        import time
        total = len(self.boot_steps)
        for i, (msg, delay) in enumerate(self.boot_steps):
            self.log.config(text=f"[ OK ] {msg}")
            progress = int((i + 1) / total * 600)
            self.progress_canvas.coords(self.progress_fill, 0, 0, progress, 6)
            time.sleep(delay)
        self.root.after(0, self.show_login)

    def show_login(self):
        self.root.destroy()
        mode = self.mode.get()
        if mode == "safe":
            os.system("bash shell/luo_shell.sh")
        elif mode == "ai":
            os.system("python3 ai_core/daemon.py")
        else:
            from ui.login import LuoLogin
            def on_login(username):
                print(f"[Luo OS] Logged in as: {username}")
                from ui.window_manager import LuoDesktop
                desktop = LuoDesktop()
                desktop.run()
            login = LuoLogin(on_success=on_login)
            login.run()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    boot = LuoOSBoot()
    boot.run()
