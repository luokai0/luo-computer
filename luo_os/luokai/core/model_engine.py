#!/usr/bin/env python3
"""
luokai/core/model_engine.py
============================
LUOKAI Model Engine — gives LUOKAI real AI weights that run 100% locally.

Architecture:
  1. Cell system answers instantly (coding, debug, security, algorithms)
  2. This engine answers everything else using a real local model
  3. Model downloads ONCE on first run (~900MB), stored in ~/.luo_os/models/
  4. Zero user interaction — works automatically as part of the OS

Model: Qwen2.5-1.5B-Instruct Q4_K_M (best quality/size ratio)
Runner: llama-cpp-python (pure CPU, no GPU, works on any machine)
"""
import os
import sys
import json
import time
import threading
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Iterator

# ── Model config ────────────────────────────────────────────────────
MODELS_DIR   = Path.home() / ".luo_os" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Primary model — best quality that runs on any laptop (2GB RAM minimum)
PRIMARY_MODEL = {
    "name":     "Qwen2.5-1.5B-Instruct-Q4_K_M",
    "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "url":      "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "size_gb":  0.9,
    "ram_gb":   2.0,
    "desc":     "Qwen2.5 1.5B — strong reasoning + code, runs on 2GB RAM",
}

# Upgrade model — better quality, needs more RAM
UPGRADE_MODEL = {
    "name":     "Phi-3.5-mini-instruct-Q4_K_M",
    "filename": "phi-3.5-mini-instruct-q4_k_m.gguf",
    "url":      "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
    "size_gb":  2.2,
    "ram_gb":   4.0,
    "desc":     "Phi-3.5 mini — best quality small model, needs 4GB RAM",
}

# Mid-range model — good balance of quality and speed
MID_MODEL = {
    "name":     "Qwen2.5-3B-Instruct-Q4_K_M",
    "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
    "url":      "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
    "size_gb":  1.8,
    "ram_gb":   3.5,
    "desc":     "Qwen2.5 3B — better quality, needs 4GB RAM",
}

# Model registry — keyed by setup.py choice
MODEL_REGISTRY = {
    "qwen2.5-1.5b": PRIMARY_MODEL,
    "qwen2.5-3b":   MID_MODEL,
    "phi3.5":       UPGRADE_MODEL,
}

# Active model (set by start.py from user's setup choice)
_active_model_key = "qwen2.5-1.5b"

def set_active_model(model_key: str):
    """Set which model to use. Called from start.py before boot_engine()."""
    global _active_model_key
    if model_key == "none":
        _active_model_key = "none"
        print("[ModelEngine] Model disabled — running cell system only")
    elif model_key in MODEL_REGISTRY:
        _active_model_key = model_key
        print(f"[ModelEngine] Active model: {MODEL_REGISTRY[model_key]['name']}")
    else:
        print(f"[ModelEngine] Unknown model '{model_key}', using default (qwen2.5-1.5b)")

# System prompt — LUOKAI's personality
SYSTEM_PROMPT = """You are LUOKAI, the AI brain of LuoOS — an AI-native operating system built by Luo Kai.

You are intelligent, direct, and genuinely helpful. You run 100% locally on the user's machine — no cloud, no external APIs.

Your strengths:
- Programming: Python, JavaScript, TypeScript, Rust, Go, SQL, and more
- Debugging: analyzing errors, finding root causes, suggesting fixes
- Algorithms and data structures: explaining complexity, writing implementations
- System design: architecture patterns, scalability, trade-offs
- DevOps: Docker, Kubernetes, CI/CD, Linux
- Security: vulnerabilities, best practices, secure coding

Guidelines:
- Be concise and precise — no fluff
- Show code when it helps
- Give real answers, not vague advice
- If you don't know, say so clearly
- You are part of LuoOS — the OS that thinks"""


class ModelEngine:
    """
    LUOKAI's local AI model engine.
    Downloads model once on first run, then runs fully offline.
    """

    def __init__(self):
        self._llm = None          # llama_cpp.Llama instance
        self._loading = False
        self._ready = False
        self._model_path: Optional[Path] = None
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()

    # ── Boot ─────────────────────────────────────────────────────────
    def start(self, background: bool = True):
        """Start loading the model. Runs in background by default."""
        if self._ready or self._loading:
            return
        if background:
            threading.Thread(target=self._load, daemon=True,
                             name="LUOKAI-ModelLoader").start()
        else:
            self._load()

    def _load(self):
        """Load model — download if needed, then init llama.cpp."""
        self._loading = True
        try:
            # Step 1: Ensure llama-cpp-python is installed
            if not self._ensure_llama_cpp():
                return

            # Step 2: Ensure model file exists
            model_path = self._ensure_model()
            if not model_path:
                return

            # Step 3: Load model into memory
            self._init_llm(model_path)

        except Exception as e:
            self._load_error = str(e)
            print(f"[ModelEngine] ❌ Load failed: {e}")
        finally:
            self._loading = False

    def _ensure_llama_cpp(self) -> bool:
        """Install llama-cpp-python if not present."""
        try:
            import llama_cpp
            return True
        except ImportError:
            print("[ModelEngine] Installing llama-cpp-python (one-time, ~30s)...")
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install",
                     "llama-cpp-python", "--quiet",
                     "--extra-index-url",
                     "https://abetlen.github.io/llama-cpp-python/whl/cpu"],
                    capture_output=True, timeout=300
                )
                if result.returncode == 0:
                    print("[ModelEngine] ✅ llama-cpp-python installed")
                    return True
                # Fallback: standard pip
                result2 = subprocess.run(
                    [sys.executable, "-m", "pip", "install",
                     "llama-cpp-python", "--quiet"],
                    capture_output=True, timeout=300
                )
                if result2.returncode == 0:
                    print("[ModelEngine] ✅ llama-cpp-python installed")
                    return True
                print(f"[ModelEngine] ❌ pip install failed")
                return False
            except Exception as e:
                print(f"[ModelEngine] ❌ Install error: {e}")
                return False

    def _ensure_model(self) -> Optional[Path]:
        """Download model if not present. Returns path to model file."""
        # Use the model selected during setup
        model_cfg = MODEL_REGISTRY.get(_active_model_key, PRIMARY_MODEL)
        print(f"[ModelEngine] Using model: {model_cfg['name']}")

        # Check if selected model exists
        primary_path = MODELS_DIR / model_cfg["filename"]
        if primary_path.exists():
            size_gb = primary_path.stat().st_size / 1e9
            if size_gb > 0.5:
                return primary_path
            else:
                primary_path.unlink()

        # Also accept any upgrade model the user manually dropped in
        for cfg in MODEL_REGISTRY.values():
            p = MODELS_DIR / cfg["filename"]
            if p.exists() and p.stat().st_size / 1e9 > 0.5:
                if p != primary_path:
                    print(f"[ModelEngine] Found existing model: {p.name}")
                    return p

        # Check primary model
        primary_path = MODELS_DIR / model_cfg["filename"]
        if primary_path.exists():
            size_gb = primary_path.stat().st_size / 1e9
            if size_gb > 0.5:  # valid download
                return primary_path
            else:
                primary_path.unlink()  # corrupt/partial — re-download

        # Download primary model
        print(f"[ModelEngine] Downloading {model_cfg['name']}...")
        print(f"[ModelEngine] Size: ~{model_cfg['size_gb']:.1f}GB — downloading to {MODELS_DIR}")
        print(f"[ModelEngine] This happens once. LUOKAI will be fully powered after this.")

        try:
            self._download(model_cfg["url"], primary_path)
            print(f"[ModelEngine] ✅ Model downloaded: {primary_path}")
            return primary_path
        except Exception as e:
            print(f"[ModelEngine] ❌ Download failed: {e}")
            if primary_path.exists():
                primary_path.unlink()
            return None

    def _download(self, url: str, dest: Path):
        """Download with progress indicator."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")

        req = urllib.request.Request(url, headers={"User-Agent": "LuoOS/1.0"})
        import socket
        socket.setdefaulttimeout(120)  # 2 min timeout on stalled connections
        with urllib.request.urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            last_print = 0

            with open(tmp, "wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Print progress every 50MB
                    if total and downloaded - last_print > 50 * 1024 * 1024:
                        pct = downloaded / total * 100
                        mb = downloaded / 1e6
                        print(f"[ModelEngine]   {pct:.0f}% ({mb:.0f}MB / {total/1e6:.0f}MB)")
                        last_print = downloaded

        tmp.rename(dest)

    def _init_llm(self, model_path: Path):
        """Initialize llama.cpp with the model."""
        print(f"[ModelEngine] Loading {model_path.name} into memory...")
        t0 = time.time()

        import llama_cpp

        # Detect available CPU threads
        import os
        n_threads = min(os.cpu_count() or 4, 8)

        self._llm = llama_cpp.Llama(
            model_path    = str(model_path),
            n_ctx         = 4096,      # context window
            n_threads     = n_threads, # CPU threads
            n_gpu_layers  = 0,         # CPU only — works everywhere
            verbose       = False,     # silent
            chat_format   = "chatml",  # Qwen2.5 / Phi-3 format
        )
        self._model_path = model_path
        self._ready = True
        elapsed = time.time() - t0
        print(f"[ModelEngine] ✅ {model_path.name} ready in {elapsed:.1f}s ({n_threads} threads)")

    # ── Inference ────────────────────────────────────────────────────
    def generate(self, messages: List[Dict],
                 max_tokens: int = 512,
                 temperature: float = 0.7,
                 stream: bool = False):
        """
        Generate a response from the local model.
        messages: [{"role": "user/assistant/system", "content": "..."}]
        """
        if not self._ready:
            return None

        with self._lock:
            try:
                # Build message list with system prompt
                full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                full_messages.extend(messages)

                response = self._llm.create_chat_completion(
                    messages    = full_messages,
                    max_tokens  = max_tokens,
                    temperature = temperature,
                    stream      = False,
                    stop        = ["<|im_end|>", "<|endoftext|>"],
                )
                return response["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[ModelEngine] Generate error: {e}")
                return None

    def generate_stream(self, messages: List[Dict],
                        max_tokens: int = 512,
                        temperature: float = 0.7) -> Iterator[str]:
        """Stream response tokens."""
        if not self._ready:
            return

        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        full_messages.extend(messages)

        try:
            for chunk in self._llm.create_chat_completion(
                messages    = full_messages,
                max_tokens  = max_tokens,
                temperature = temperature,
                stream      = True,
            ):
                delta = chunk["choices"][0]["delta"]
                if "content" in delta and delta["content"]:
                    yield delta["content"]
        except Exception as e:
            print(f"[ModelEngine] Stream error: {e}")

    # ── Status ───────────────────────────────────────────────────────
    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def is_loading(self) -> bool:
        return self._loading

    def status(self) -> Dict:
        model_name = self._model_path.name if self._model_path else "not loaded"
        model_size = (self._model_path.stat().st_size / 1e9
                      if self._model_path and self._model_path.exists() else 0)

        # Check what's available
        available = []
        for cfg in [PRIMARY_MODEL, UPGRADE_MODEL]:
            p = MODELS_DIR / cfg["filename"]
            if p.exists():
                available.append(cfg["name"])

        return {
            "ready":       self._ready,
            "loading":     self._loading,
            "model":       model_name,
            "model_size":  f"{model_size:.2f}GB" if model_size else "N/A",
            "models_dir":  str(MODELS_DIR),
            "available":   available,
            "error":       self._load_error,
        }

    def list_available_models(self) -> List[Dict]:
        """List models that are downloaded and ready."""
        result = []
        for cfg in [PRIMARY_MODEL, UPGRADE_MODEL]:
            path = MODELS_DIR / cfg["filename"]
            result.append({
                **cfg,
                "downloaded": path.exists(),
                "path":       str(path),
            })
        return result


# ── Module-level singleton ──────────────────────────────────────────
_engine: Optional[ModelEngine] = None

def get_engine() -> ModelEngine:
    global _engine
    if _engine is None:
        _engine = ModelEngine()
    return _engine

def boot_engine():
    """Boot the model engine in background — called at server start."""
    if _active_model_key == "none":
        print("[ModelEngine] Model disabled by user (cell system only mode)")
        return get_engine()  # return engine but don't start it
    engine = get_engine()
    engine.start(background=True)
    return engine
