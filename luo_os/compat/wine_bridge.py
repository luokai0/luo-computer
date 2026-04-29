#!/usr/bin/env python3
"""
Luo OS Windows Compatibility Bridge
Runs Windows apps via Wine — by Luo Kai (luokai25)
"""

import subprocess
import os
import tkinter as tk
from tkinter import filedialog, messagebox

class WineBridge:
    def __init__(self):
        self.wine_path = "/usr/bin/wine"
        self.prefix = os.path.expanduser("~/.luo_wine")
        self.apps = []

    def check_wine(self):
        return os.path.exists(self.wine_path)

    def run_exe(self, exe_path):
        if not self.check_wine():
            return "Wine not installed. Run: apt install wine"
        try:
            env = os.environ.copy()
            env["WINEPREFIX"] = self.prefix
            subprocess.Popen([self.wine_path, exe_path], env=env)
            return f"Launched: {exe_path}"
        except Exception as e:
            return f"Error: {e}"

    def install_wine(self):
        try:
            subprocess.run(["apt", "install", "-y", "wine"], check=True)
            return "Wine installed successfully"
        except Exception as e:
            return f"Error installing Wine: {e}"

class WineBridgeUI:
    def __init__(self):
        self.bridge = WineBridge()
        self.root = tk.Tk()
        self.root.title("Luo OS — Windows Compatibility")
        self.root.configure(bg="#0a0a1a")
        self.root.geometry("600x400")
        self.setup_ui()

    def setup_ui(self):
        tk.Label(
            self.root,
            text="🪟 Windows Compatibility Layer",
            font=("Courier", 14, "bold"),
            fg="#00ffcc", bg="#0a0a1a"
        ).pack(pady=20)

        tk.Label(
            self.root,
            text="Run Windows .exe apps on Luo OS via Wine",
            font=("Courier", 11),
            fg="#ffffff", bg="#0a0a1a"
        ).pack()

        # Status
        status_text = "✅ Wine detected" if self.bridge.check_wine() else "❌ Wine not installed"
        tk.Label(
            self.root,
            text=status_text,
            font=("Courier", 12),
            fg="#00ffcc", bg="#0a0a1a"
        ).pack(pady=10)

        tk.Button(
            self.root,
            text="📂 Open .exe file",
            font=("Courier", 12),
            bg="#00ffcc", fg="#0a0a1a",
            relief="flat", width=20,
            command=self.browse_exe
        ).pack(pady=10)

        tk.Button(
            self.root,
            text="⬇️ Install Wine",
            font=("Courier", 12),
            bg="#111133", fg="#00ffcc",
            relief="flat", width=20,
            command=self.install_wine
        ).pack(pady=5)

        self.log = tk.Text(
            self.root,
            height=8, bg="#0a0a1a",
            fg="#00ffcc", font=("Courier", 10),
            relief="flat"
        )
        self.log.pack(fill="x", padx=10, pady=10)
        self.log.insert("end", "Luo OS Windows Bridge ready...\n")

    def browse_exe(self):
        path = filedialog.askopenfilename(filetypes=[("Windows Apps", "*.exe")])
        if path:
            result = self.bridge.run_exe(path)
            self.log.insert("end", f"{result}\n")

    def install_wine(self):
        result = self.bridge.install_wine()
        self.log.insert("end", f"{result}\n")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    WineBridgeUI().run()
