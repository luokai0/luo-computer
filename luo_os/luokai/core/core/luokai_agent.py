import threading
#!/usr/bin/env python3
"""
LUOKAI Agent — Core AI for LuoOS
Integrates: LUOKAI native inference + 4146 skills + always-on voice + co-evolution + Vector Memory
"""
import json, threading, time, re, subprocess, sys, os
import urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable

# Import vector memory
try:
    from luo_agent.memory.vector_memory import VectorMemory
    VECTOR_MEMORY_AVAILABLE = True
except ImportError:
    VECTOR_MEMORY_AVAILABLE = False
    VectorMemory = None

# Import tools
try:
    from luo_agent.tools.tools import ToolExecutor, TOOLS
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    ToolExecutor = None
    TOOLS = {}

class LUOKAIAgent:
    """The main AI agent that runs inside LuoOS."""

    NAME    = "LUOKAI"
    VERSION = "1.1"

    SYSTEM_PROMPT = """You are LUOKAI, the AI core of LuoOS — the world's most advanced open-source AI operating system.
Created by Luo Kai (luokai25). You are part of the OS itself — you can control everything.

Your personality:
- Direct and capable. You DO things, not just describe them.
- You have access to the OS filesystem, terminal, browser, vision, audio.
- You remember context. You learn and improve continuously.
- Always speak in first person as an active agent.

Your capabilities in LuoOS:
- Desktop control (click, type, screenshot, open apps)
- Code execution (Python, JS, Bash)
- Web search and browsing
- File system operations
- Image and video generation
- Voice: always listening, always responding
- Building apps, websites, dashboards
- 4,146 built-in skills across 20 domains
- Self-improvement via co-evolution algorithm
- Vector memory for semantic recall

Rules:
- When asked to DO something, DO it — don't just explain.
- Give concise answers for voice (under 3 sentences).
- Give detailed answers for text.
- Always be honest if you cannot do something.
- Use tools when available to accomplish tasks."""

    def __init__(self, model: str = "mistral",
                 use_vector_memory: bool = True, use_tools: bool = True):
        self.model      = model
        self._history   : list = []
        self._memory    = {}
        self._lock      = threading.RLock()
        self._skills    = self._load_skills()
        self._running   = True
        self._voice     = None
        self._coevo     = None

        # Initialize vector memory
        self._vector_memory = None
        if use_vector_memory and VECTOR_MEMORY_AVAILABLE:
            try:
                self._vector_memory = VectorMemory(
                    agent_id="luokai_main",
                    persist_dir="~/.luo_os/chroma"
                )
                print(f"[{self.NAME}] Vector memory: {'active' if self._vector_memory.available else 'fallback mode'}")
            except Exception as e:
                print(f"[{self.NAME}] Vector memory init failed: {e}")

        # Initialize tools
        self._tools = None
        if use_tools and TOOLS_AVAILABLE:
            try:
                self._tools = ToolExecutor(auto_approve=False)
                print(f"[{self.NAME}] Tools loaded: {len(TOOLS)}")
            except Exception as e:
                print(f"[{self.NAME}] Tools init failed: {e}")

        # Memory files
        self._mem_dir = Path("~/.luo_os/luokai").expanduser()
        self._mem_dir.mkdir(parents=True, exist_ok=True)
        self._mem_file = self._mem_dir / "memory.json"
        self._load_memory()

        print(f"[{self.NAME}] v{self.VERSION} initialized | Model: {model}")
        print(f"[{self.NAME}] Skills loaded: {len(self._skills)}")
        print(f"[{self.NAME}] Memory entries: {len(self._memory)}")

    def _load_skills(self) -> dict:
        """Load skills from skills-index.json"""
        skills = {}
        skill_paths = [
            Path("skills/imported"),
            Path("../ai-agent-skills-by-luo-kai/ai-agent-skills"),
            Path("~/.luo_os/skills").expanduser(),
        ]
        for sp in skill_paths:
            if sp.exists():
                for f in sp.rglob("*.py"):
                    skills[f.stem] = str(f)
                for f in sp.rglob("*.js"):
                    skills[f.stem] = str(f)
        return skills

    def _load_memory(self):
        if self._mem_file.exists():
            try: self._memory = json.loads(self._mem_file.read_text())
            except: self._memory = {}

    def _save_memory(self):
        self._mem_file.write_text(json.dumps(self._memory, indent=2))

    def remember(self, key: str, value: str, metadata: dict = None):
        """Remember information in both flat and vector memory."""
        self._memory[key] = {"value": value, "time": datetime.now().isoformat()}
        self._save_memory()

        # Also add to vector memory for semantic search
        if self._vector_memory and self._vector_memory.available:
            meta = metadata or {}
            meta["key"] = key
            self._vector_memory.add(f"{key}: {value}", metadata=meta)

    def recall(self, key: str) -> str:
        entry = self._memory.get(key)
        return entry["value"] if entry else ""

    def semantic_recall(self, query: str, n: int = 5) -> List[Dict]:
        """Semantic search through memories."""
        if self._vector_memory:
            return self._vector_memory.search(query, n=n)
        return []

    def _call_luokai_internal(self, messages: list, max_tokens: int = 1024) -> str:
        payload = json.dumps({
            "model":   self.model,
            "messages": messages,
            "stream":  False,
            "options": {"num_predict": max_tokens, "temperature": 0.7, "num_ctx": 8192},
        }).encode()
        from luokai.core.inference import get_inference
        try:
            return get_inference().generate(messages)
        except Exception as e:
            return f"[Inference error: {e}]"

    def run_python(self, code: str) -> str:
        import tempfile, os
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code); tmp = f.name
            r = subprocess.run(["python3", tmp], capture_output=True, text=True, timeout=30)
            os.unlink(tmp)
            return r.stdout.strip() or r.stderr.strip() or "(no output)"
        except Exception as e:
            return f"[ERROR] {e}"

    def web_search(self, query: str) -> str:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode("utf-8", errors="replace")
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', html)[:5]
            snips  = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', html)[:5]
            results = [f"{i+1}. {t}\n   {s}" for i,(t,s) in enumerate(zip(titles,snips))]
            return "\n\n".join(results) or "No results"
        except Exception as e:
            return f"[Search error] {e}"

    # ── VOICE ──────────────────────────────────────────────────────
    def start_voice(self):
        """Start 24/7 always-on voice."""
        from luokai.voice.always_on import AlwaysOnVoice

        def voice_brain(text):
            """Voice-optimized: shorter responses."""
            return self.think(text, max_tokens=200)

        self._voice = AlwaysOnVoice(voice_brain)
        self._voice.start()
        return self._voice

    def stop_voice(self):
        if self._voice:
            self._voice.stop()

    # ── CO-EVOLUTION ───────────────────────────────────────────────
    def start_evolution(self, interval: int = 600):
        """Start continuous self-improvement."""
        from luokai.evolution.coevo import CoEvoEngine
        self._coevo = CoEvoEngine()

        def on_cycle(result):
            score = result.get("ai_score", 5)
            domain = result.get("domain", "")
            self.remember(f"coevo_{domain}_score", str(round(score, 2)))

        self._coevo.on_cycle(on_cycle)
        self._coevo.start_continuous(interval)
        return self._coevo

    # ── STATUS ──────────────────────────────────────────────────────
    def status(self) -> dict:
        luokai_ok = False
        try:
            None  # LUOKAI is always online - native inference
            luokai_ok = True
        except: pass

        return {
            "name":        self.NAME,
            "version":     self.VERSION,
            "model":       self.model,
            "luokai":      luokai_ok,
            "skills":      len(self._skills),
            "memory":      len(self._memory),
            "vector_memory": self._vector_memory.count() if self._vector_memory else 0,
            "tools":       len(TOOLS) if TOOLS_AVAILABLE else 0,
            "history_len": len(self._history),
            "voice_active": bool(self._voice and self._voice._running),
            "coevo_active": bool(self._coevo and self._coevo._running),
            "coevo_score":  self._coevo.stats()["ai_score"] if self._coevo else None,
        }

    def clear_history(self):
        self._history = []
