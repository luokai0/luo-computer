#!/usr/bin/env python3
"""LUOKAI LLM Client — routes to LUOKAI native inference engine."""
import urllib.request
import json, json

class OllamaClient:
    """Compatibility shim — routes to LUOKAI native inference."""
    def __init__(self, url="http://localhost:3000", model="luokai"):
        self.url   = "http://localhost:3000"
        self.model = "luokai"

    def chat(self, prompt: str, system: str = "") -> str:
        try:
            payload = json.dumps({"message": prompt}).encode()
            req = urllib.request.Request(
                f"{self.url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                return data.get("response", "") or data.get("content", "")
        except Exception as e:
            return f"[LUOKAI] {e}"

    def generate(self, prompt: str) -> str:
        return self.chat(prompt)

    def is_available(self) -> bool:
        try:
            urllib.request.urlopen("http://localhost:3000/api/status", timeout=2)
            return True
        except Exception:
            return False
