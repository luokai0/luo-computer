#!/usr/bin/env python3
"""
Luo OS Login Screen
Human and AI Agent authentication
Created by Luo Kai (luokai25)
"""

import tkinter as tk
import hashlib
import json
import os
from datetime import datetime

USERS_FILE = os.path.expanduser("~/.luo_users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    # Default users
    return {
        "kai": {"password": hashlib.sha256("kai123".encode()).hexdigest(), "role": "admin"},
        "ai_agent": {"password": hashlib.sha256("agent".encode()).hexdigest(), "role": "agent"},
        "guest": {"password": hashlib.sha256("guest".encode()).hexdigest(), "role": "guest"}
    }

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

class LuoLogin:
    def __init__(self, on_success=None):
        self.on_success = on_success
        self.users = load_users()
        save_users(self.users)
        self.root = tk.Tk()
        self.root.title("Luo OS — Login")
        self.root.configure(bg="#0a0a1a")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        self.setup_ui()

    def setup_ui(self):
        # Logo
        tk.Label(self.root, text="⚡", font=("Courier", 50), fg="#00ffcc", bg="#0a0a1a").pack(pady=30)
        tk.Label(self.root, text="LUO OS", font=("Courier", 36, "bold"), fg="#00ffcc", bg="#0a0a1a").pack()
        tk.Label(self.root, text="Free OS for Humans & AI Agents", font=("Courier", 11), fg="#aaaaaa", bg="#0a0a1a").pack(pady=5)

        # Login frame
        frame = tk.Frame(self.root, bg="#111133", padx=30, pady=30)
        frame.pack(pady=30, padx=50, fill="x")

        tk.Label(frame, text="Username", font=("Courier", 11), fg="#00ffcc", bg="#111133", anchor="w").pack(fill="x")
        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(frame, textvariable=self.username_var, font=("Courier", 13),
                                        bg="#0a0a1a", fg="#fff", insertbackground="#00ffcc",
                                        relief="flat", bd=5)
        self.username_entry.pack(fill="x", pady=(3, 15))
        self.username_entry.insert(0, "kai")

        tk.Label(frame, text="Password", font=("Courier", 11), fg="#00ffcc", bg="#111133", anchor="w").pack(fill="x")
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(frame, textvariable=self.password_var, font=("Courier", 13),
                                        bg="#0a0a1a", fg="#fff", insertbackground="#00ffcc",
                                        relief="flat", bd=5, show="●")
        self.password_entry.pack(fill="x", pady=(3, 20))
        self.password_entry.bind("<Return>", lambda e: self.login())

        # Login mode
        self.mode_var = tk.StringVar(value="human")
        mode_frame = tk.Frame(frame, bg="#111133")
        mode_frame.pack(fill="x", pady=(0, 20))
        tk.Label(mode_frame, text="Mode:", font=("Courier", 10), fg="#aaa", bg="#111133").pack(side="left")
        for text, val in [(" Human", "human"), (" AI Agent", "agent")]:
            tk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=val,
                          font=("Courier", 10), fg="#00ffcc", bg="#111133",
                          selectcolor="#0a0a1a", activebackground="#111133").pack(side="left", padx=5)

        tk.Button(frame, text="LOGIN →", font=("Courier", 13, "bold"),
                 bg="#00ffcc", fg="#0a0a1a", relief="flat", command=self.login).pack(fill="x", pady=5)

        tk.Button(frame, text="Guest Mode", font=("Courier", 11),
                 bg="#111133", fg="#00ffcc", relief="flat", command=self.guest_login).pack(fill="x")

        self.msg = tk.Label(self.root, text="", font=("Courier", 11), fg="#ff4444", bg="#0a0a1a")
        self.msg.pack()

        tk.Label(self.root, text="by Luo Kai (luokai25)", font=("Courier", 9),
                fg="#333355", bg="#0a0a1a").pack(side="bottom", pady=10)

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        hashed = hashlib.sha256(password.encode()).hexdigest()

        if username in self.users and self.users[username]["password"] == hashed:
            self.msg.config(text=f"Welcome, {username}!", fg="#00ffcc")
            self.root.after(800, lambda: self.launch(username))
        else:
            self.msg.config(text="❌ Invalid username or password", fg="#ff4444")

    def guest_login(self):
        self.launch("guest")

    def launch(self, username):
        self.root.destroy()
        if self.on_success:
            self.on_success(username)
        else:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from ui.window_manager import LuoDesktop
            desktop = LuoDesktop()
            desktop.run()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    login = LuoLogin()
    login.run()
