#!/usr/bin/env python3
"""
Luo OS Text Editor — Free built-in app
by Luo Kai (luokai25)
"""

import tkinter as tk
from tkinter import filedialog, messagebox

class LuoEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Luo Editor v0.1")
        self.root.configure(bg="#0a0a1a")
        self.root.geometry("800x600")
        self.current_file = None
        self.setup_menu()
        self.setup_editor()

    def setup_menu(self):
        menubar = tk.Menu(self.root, bg="#111133", fg="#00ffcc")
        
        file_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#00ffcc")
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self.root.config(menu=menubar)

    def setup_editor(self):
        # Toolbar
        toolbar = tk.Frame(self.root, bg="#111133", height=40)
        toolbar.pack(fill="x")

        for text, cmd in [("New", self.new_file), ("Open", self.open_file), ("Save", self.save_file)]:
            tk.Button(
                toolbar, text=text,
                font=("Courier", 11),
                bg="#00ffcc", fg="#0a0a1a",
                relief="flat", command=cmd
            ).pack(side="left", padx=5, pady=5)

        # Editor
        self.text = tk.Text(
            self.root,
            bg="#0a0a1a", fg="#ffffff",
            font=("Courier", 12),
            insertbackground="#00ffcc",
            relief="flat",
            wrap="word"
        )
        self.text.pack(fill="both", expand=True, padx=5, pady=5)

        # Status bar
        self.status = tk.Label(
            self.root,
            text="Luo Editor — Ready",
            font=("Courier", 10),
            fg="#00ffcc", bg="#111133",
            anchor="w"
        )
        self.status.pack(fill="x", side="bottom")

    def new_file(self):
        self.text.delete(1.0, "end")
        self.current_file = None
        self.status.config(text="New file")

    def open_file(self):
        path = filedialog.askopenfilename()
        if path:
            with open(path, "r") as f:
                self.text.delete(1.0, "end")
                self.text.insert("end", f.read())
            self.current_file = path
            self.status.config(text=f"Opened: {path}")

    def save_file(self):
        if self.current_file:
            with open(self.current_file, "w") as f:
                f.write(self.text.get(1.0, "end"))
            self.status.config(text=f"Saved: {self.current_file}")
        else:
            path = filedialog.asksaveasfilename()
            if path:
                with open(path, "w") as f:
                    f.write(self.text.get(1.0, "end"))
                self.current_file = path
                self.status.config(text=f"Saved: {path}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    LuoEditor().run()
