#!/usr/bin/env python3
"""
Luo OS File Manager — Free built-in app
by Luo Kai (luokai25)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil

class LuoFiles:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Luo Files v0.1")
        self.root.configure(bg="#0a0a1a")
        self.root.geometry("800x600")
        self.current_path = os.path.expanduser("~")
        self.setup_ui()
        self.load_directory()

    def setup_ui(self):
        # Path bar
        top = tk.Frame(self.root, bg="#111133")
        top.pack(fill="x")

        self.path_label = tk.Label(
            top, text=self.current_path,
            font=("Courier", 11),
            fg="#00ffcc", bg="#111133"
        )
        self.path_label.pack(side="left", padx=10, pady=8)

        tk.Button(top, text="⬆ Up", font=("Courier", 11), bg="#111133", fg="#00ffcc", relief="flat", command=self.go_up).pack(side="right", padx=10)

        # File list
        self.listbox = tk.Listbox(
            self.root,
            bg="#0a0a1a", fg="#ffffff",
            font=("Courier", 12),
            selectbackground="#00ffcc",
            selectforeground="#0a0a1a",
            relief="flat"
        )
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.listbox.bind("<Double-Button-1>", self.on_double_click)

        # Status
        self.status = tk.Label(
            self.root, text="",
            font=("Courier", 10),
            fg="#00ffcc", bg="#111133", anchor="w"
        )
        self.status.pack(fill="x", side="bottom")

    def load_directory(self):
        self.listbox.delete(0, "end")
        try:
            items = sorted(os.listdir(self.current_path))
            for item in items:
                full = os.path.join(self.current_path, item)
                prefix = "📁 " if os.path.isdir(full) else "📄 "
                self.listbox.insert("end", prefix + item)
            self.path_label.config(text=self.current_path)
            self.status.config(text=f"{len(items)} items")
        except PermissionError:
            self.status.config(text="Permission denied")

    def on_double_click(self, event):
        selection = self.listbox.get(self.listbox.curselection())
        name = selection[3:]
        full_path = os.path.join(self.current_path, name)
        if os.path.isdir(full_path):
            self.current_path = full_path
            self.load_directory()

    def go_up(self):
        self.current_path = os.path.dirname(self.current_path)
        self.load_directory()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    LuoFiles().run()
