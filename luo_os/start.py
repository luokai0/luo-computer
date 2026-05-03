#!/usr/bin/env python3
"""
LuoOS — Start
Windows: double-click start.bat  |  Mac/Linux: ./start.sh
"""
import os, sys, subprocess, time, socket, threading, webbrowser
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# ── Colours ─────────────────────────────────────────────────────────
C="\033[96m"; G="\033[92m"; Y="\033[93m"; R="\033[0m"
B="\033[1m";  DIM="\033[2m"; W="\033[97m"

step = lambda m: print(f"{G}  ✅  {m}{R}")
warn = lambda m: print(f"{Y}  ⚠️   {m}{R}")
info = lambda m: print(f"{C}  →   {m}{R}")

# ── Python version gate ─────────────────────────────────────────────
if sys.version_info < (3, 6):
    print("\n  LuoOS needs Python 3.6+  →  https://python.org/downloads\n")
    input("Press Enter to exit..."); sys.exit(1)

# ── Auto-install core deps ──────────────────────────────────────────
import importlib.util
missing = [pip for mod, pip in [
    ("flask","flask"),("flask_cors","flask-cors"),("playwright","playwright"),
] if not importlib.util.find_spec(mod)]
if missing:
    print(f"\n  Installing: {', '.join(missing)}  (one-time)…\n")
    try:
        subprocess.check_call([sys.executable,"-m","pip","install","--quiet"]+missing,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        step(f"Installed: {', '.join(missing)}")
        # Install Chromium binary if playwright was just installed
        if "playwright" in missing:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                step("Headless Chromium installed — browser can load any site")
            except Exception:
                pass
    except Exception:
        warn(f"Run: pip install {' '.join(missing)}")
        input("Press Enter to exit..."); sys.exit(1)

# ── Run setup wizard if first launch ───────────────────────────────
from setup_luoos import ensure_setup, load_config

print(f"\n{B}{C}  LuoOS{R}")
print(f"  {DIM}{'─'*40}{R}\n")

config = ensure_setup()   # shows wizard on first run, returns config

# ── Read config values ──────────────────────────────────────────────
USER_NAME    = config.get("user_name", "User")
AI_MODEL     = config.get("ai_model", "qwen2.5-1.5b")
PORT         = int(config.get("port", 3000))
AUTO_BROWSER = config.get("auto_open_browser", True)
FEATURES     = config.get("features", {})
SHOW_TIPS    = config.get("show_startup_tips", True)

# ── Banner ───────────────────────────────────────────────────────────
print(f"""
{B}{C}  ██╗     ██╗   ██╗ ██████╗      ██████╗ ███████╗
  ██║     ██║   ██║██╔═══██╗    ██╔═══██╗██╔════╝
  ██║     ██║   ██║██║   ██║    ██║   ██║███████╗
  ██║     ██║   ██║██║   ██║    ██║   ██║╚════██║
  ███████╗╚██████╔╝╚██████╔╝    ╚██████╔╝███████║
  ╚══════╝ ╚═════╝  ╚═════╝      ╚═════╝ ╚══════╝{R}
""")

# ── Port check ───────────────────────────────────────────────────────
def port_free(p):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", p)) != 0

if not port_free(PORT):
    PORT += 1
    warn(f"Port busy — using {PORT}")

os.environ["LUO_PORT"]      = str(PORT)
os.environ["LUO_USER_NAME"] = USER_NAME
os.environ["LUO_AI_MODEL"]  = AI_MODEL
os.environ["LUO_FEATURES"]  = ",".join(k for k,v in FEATURES.items() if v)
url = f"http://localhost:{PORT}"

# ── Startup info ────────────────────────────────────────────────────
print(f"  {DIM}{'─'*54}{R}")
info(f"Welcome back, {W}{USER_NAME}{R}")
info(f"Starting LuoOS  →  {G}{url}{R}")

# Model status
from luokai.core.model_engine import MODELS_DIR, PRIMARY_MODEL, UPGRADE_MODEL

def _model_size(model_key):
    sizes = {"qwen2.5-1.5b":"900MB","qwen2.5-3b":"1.8GB","phi3.5":"2.2GB"}
    return sizes.get(model_key, "~1GB")

MODEL_FILES = {
    "qwen2.5-1.5b": PRIMARY_MODEL["filename"],
    "qwen2.5-3b":   "qwen2.5-3b-instruct-q4_k_m.gguf",
    "phi3.5":       UPGRADE_MODEL["filename"],
    "none":         None,
}
model_file = MODEL_FILES.get(AI_MODEL)
if model_file:
    model_path = MODELS_DIR / model_file
    if model_path.exists():
        step(f"AI model ready: {model_path.name}")
    else:
        info(f"AI model: downloading {AI_MODEL} on first use (~{_model_size(AI_MODEL)})")
else:
    info("AI: cell system + knowledge base (instant)")

# Features
active = [k for k, v in FEATURES.items() if v]
if active:
    info(f"Features: {', '.join(active)}")

if SHOW_TIPS:
    info(f"Press Ctrl+C to stop  ·  Reconfigure: python3 setup_luoos.py --reset")
print(f"  {DIM}{'─'*54}{R}\n")

# ── Browser opener ───────────────────────────────────────────────────
def open_browser():
    for _ in range(40):
        time.sleep(0.5)
        if not port_free(PORT):
            time.sleep(0.8)
            webbrowser.open(url)
            return
    webbrowser.open(url)

if AUTO_BROWSER:
    threading.Thread(target=open_browser, daemon=True).start()

# ── Boot ─────────────────────────────────────────────────────────────
try:
    import luo_server
    luo_server._run_server()
except KeyboardInterrupt:
    print(f"\n\n  {Y}LuoOS stopped.{R}  See you next time, {USER_NAME}.\n")
    sys.exit(0)
except Exception as e:
    print(f"\n  ❌  {e}\n  Try: python3 luo_server.py")
    input("\nPress Enter to exit..."); sys.exit(1)
