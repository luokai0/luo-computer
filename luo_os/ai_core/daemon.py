#!/usr/bin/env python3
"""
Luo OS AI Core Daemon v0.3 — With Memory
Powered by LUOKAI native inference engine
Created by Luo Kai (luokai25)
"""

import os
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from memory import remember, recall, get_context, learn_fact, get_fact, stats

LUOKAI_API = "http://127.0.0.1:3000/api/chat"
MODEL = "tinyllama"

SYSTEM_PROMPT = """You are Luo AI, the intelligent core of Luo OS.
Created by Luo Kai. You have memory of past conversations.
Be concise. Max 2 sentences per response."""

class LuoAI:
    def __init__(self):
        self.name = "Luo AI"
        self.version = "0.3"
        self.running = True
        print(f"╔══════════════════════════════════════╗")
        print(f"║   LUO OS — AI Core v{self.version}              ║")
        print(f"║   Powered by TinyLlama + Memory      ║")
        print(f"║   Free for Humans & AI Agents        ║")
        print(f"╚══════════════════════════════════════╝")
        s = stats()
        print(f"[Memory] {s['total_conversations']} past conversations loaded")
        print(f"[Memory] {s['total_facts']} facts stored\n")

    def check_luokai(self):
        try:
            urllib.request.urlopen("http://127.0.0.1:3000/api/status", timeout=3)
            return True
        except:
            return False

    def think(self, user_input):
        # Get memory context
        context = get_context(limit=5)
        prompt = f"{SYSTEM_PROMPT}\n\nPast conversations:\n{context}\n\nUser: {user_input}\nLuo AI:" if context else f"{SYSTEM_PROMPT}\n\nUser: {user_input}\nLuo AI:"

        payload = json.dumps({
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 80,
                "temperature": 0.7,
                "num_ctx": 512
            }
        }).encode()

        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
                result = json.loads(raw.decode()) if raw else {}
                response = result.get("response", "").strip()
                remember(user_input, response)
                return response
        except Exception as e:
            return f"[Error] {e}"

    def handle_special(self, text):
        t = text.lower().strip()
        if t == "memory stats":
            s = stats()
            return f"Conversations: {s['total_conversations']} | Facts: {s['total_facts']}"
        elif t.startswith("remember that "):
            parts = text[14:].split(" is ", 1)
            if len(parts) == 2:
                learn_fact(parts[0].strip(), parts[1].strip())
                return f"Got it! I'll remember that {parts[0].strip()} is {parts[1].strip()}"
        elif t.startswith("what is "):
            key = text[8:].strip()
            fact = get_fact(key)
            if fact:
                return f"{key} is {fact['value']}"
        elif t == "recall":
            memories = recall(limit=3)
            if not memories:
                return "No memories yet."
            return "\n".join([f"- {m['user']}" for m in memories])
        return None

    def run(self):
        print("[Luo AI] LUOKAI connected ✅")
        print(f"[Luo AI] Ready. Type 'memory stats', 'recall', or 'exit'\n")

        while self.running:
            try:
                user_input = input("You → ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    print("[Luo AI] Goodbye. Your conversation is saved.")
                    break
                special = self.handle_special(user_input)
                if special:
                    print(f"Luo AI → {special}\n")
                    continue
                print("[Luo AI] Thinking...")
                response = self.think(user_input)
                print(f"Luo AI → {response}\n")
            except KeyboardInterrupt:
                print("\n[Luo AI] Memory saved. Goodbye.")
                break

if __name__ == "__main__":
    ai = LuoAI()
    ai.run()
