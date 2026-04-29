#!/usr/bin/env python3
"""
Luo OS Browser — Free built-in web browser
by Luo Kai (luokai25)
"""

import tkinter as tk
from tkinter import ttk
import urllib.request

class LuoBrowser:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Luo Browser v0.1")
        self.root.configure(bg="#0a0a1a")
        self.root.geometry("1024x768")
        self.setup_browser()

    def setup_browser(self):
        # Navigation bar
        nav = tk.Frame(self.root, bg="#111133", height=50)
        nav.pack(fill="x")

        tk.Button(nav, text="←", font=("Courier", 14), bg="#111133", fg="#00ffcc", relief="flat").pack(side="left", padx=5)
        tk.Button(nav, text="→", font=("Courier", 14), bg="#111133", fg="#00ffcc", relief="flat").pack(side="left", padx=5)
        tk.Button(nav, text="⟳", font=("Courier", 14), bg="#111133", fg="#00ffcc", relief="flat", command=self.load_page).pack(side="left", padx=5)

        self.url_bar = tk.Entry(
            nav, font=("Courier", 12),
            bg="#0a0a1a", fg="#ffffff",
            insertbackground="#00ffcc",
            relief="flat", width=80
        )
        self.url_bar.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        self.url_bar.insert(0, "https://")
        self.url_bar.bind("<Return>", lambda e: self.load_page())

        tk.Button(nav, text="Go →", font=("Courier", 12), bg="#00ffcc", fg="#0a0a1a", relief="flat", command=self.load_page).pack(side="left", padx=5)

        # Content area
        self.content = tk.Text(
            self.root,
            bg="#0a0a1a", fg="#ffffff",
            font=("Courier", 11),
            relief="flat", wrap="word"
        )
        self.content.pack(fill="both", expand=True, padx=5, pady=5)
        self.content.insert("end", "Welcome to Luo Browser\nEnter a URL and press Go →")

        # Status
        self.status = tk.Label(
            self.root, text="Ready",
            font=("Courier", 10),
            fg="#00ffcc", bg="#111133", anchor="w"
        )
        self.status.pack(fill="x", side="bottom")

    def load_page(self):
        url = self.url_bar.get()
        self.status.config(text=f"Loading {url}...")
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                html = r.read().decode("utf-8", errors="ignore")
            self.content.delete(1.0, "end")
            self.content.insert("end", html[:5000])
            self.status.config(text=f"Loaded: {url}")
        except Exception as e:
            self.content.delete(1.0, "end")
            self.content.insert("end", f"Error loading page:\n{e}")
            self.status.config(text="Error")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    LuoBrowser().run()
