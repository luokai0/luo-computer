# LuoOS — The AI-Native Operating System

> **Built by Luo Kai.** An OS where the AI *is* the system.

LUOKAI runs 100% locally — no Ollama, no OpenAI, no cloud. Run it and it works.

---

## Quick Start

```bash
git clone https://github.com/luokai25/luo_os-v_0.1.git
cd luo_os-v_0.1
python3 start.py
```

Opens at `http://localhost:3000`. First run shows a setup wizard — takes 60 seconds.

**Windows:** double-click `start.bat` · **Mac/Linux:** `./start.sh`

---

## How to Run

| Method | Command |
|---|---|
| Windows | Double-click `start.bat` |
| Mac / Linux | `./start.sh` |
| Any Python 3.6+ | `python3 start.py` |
| GitHub Codespaces | Code → Codespaces → `python3 start.py` |
| Docker | `docker run -p 3000:3000 -v ~/.luo_os:/root/.luo_os luokai25/luo_os` |
| pip | `pip install luo-os && luo-os start` |
| Replit | Import from GitHub → Run |
| Gitpod | `https://gitpod.io/#https://github.com/luokai25/luo_os-v_0.1` |
| VS Code Dev Container | Open folder → "Reopen in Container" |
| Linux server | `python3 luo_server.py` |

---

## First-Run Setup Wizard

Six steps, runs once on first launch (`setup_luoos.py`):

1. **Name** — LUOKAI personalises every greeting with it
2. **AI Model** — wizard detects your RAM and recommends:
   - Under 4GB → Qwen2.5 1.5B (900MB)
   - 4–8GB → Qwen2.5 3B (1.8GB)
   - 8GB+ → Phi-3.5 mini (2.2GB, best quality)
   - Or skip — cell system answers most things instantly
3. **API Keys** — 60 providers: OpenAI, Anthropic, GitHub, Stripe, etc. (all optional, stored locally)
4. **Appearance** — 5 themes + wallpaper styles, applied live to `index.html`
5. **Features** — voice, co-evolution, neural interface, auto-learn (independent toggles)
6. **Startup** — port, auto-open browser, headless Chromium install (for full browser)

Reset: `python3 setup_luoos.py --reset`

---

## Built-In Apps

| App | What it does |
|---|---|
| **🤖 LUOKAI AI** | Full AI chat with persistent memory across sessions |
| **💻 VS Code** | Monaco editor — syntax highlighting, intellisense, file tree, integrated terminal, Ask LUOKAI |
| **🌐 Browser** | Headless Chromium engine — Google, YouTube, Twitter, every site works |
| **🌍 WorldMonitor** | Live global news from 335 RSS feeds, 10 categories, ask LUOKAI about headlines |
| **📁 Files** | File manager — browse, open, upload, delete, create folders |
| **💻 Terminal** | Real bash/shell terminal with command history, Tab completion stub, `luokai <q>` built-in |
| **📝 Notes** | Rich notes with AI improvement, multiple notes, word count, auto-save |
| **🎵 Music** | YouTube embed player + quick-play presets (lo-fi, jazz, classical, synthwave) |
| **🧮 Calculator** | iOS-style calculator with full arithmetic |
| **📅 Calendar** | Monthly calendar with events, add/delete, persisted in localStorage |
| **⚙️ Settings** | 9 working tabs: Appearance, LUOKAI AI, Voice, Evolution, API Keys, Themes, System, Privacy, Network |

---

## LUOKAI Brain

No external dependencies. Zero cloud calls.

```
Routing order (fastest → slowest):
  1. Identity / math / greet         → instant
  2. Coding cells (debug/algo)       → instant
  3. Knowledge DB (78,063 entries)   → instant
  4. Local model weights (Qwen/Phi)  → ~1–3s
  5. Skills library (4,146 entries)  → instant
```

### Cell System

| Family | Count | Cells |
|---|---|---|
| Reasoning | 14 | ModusPonens, Syllogism, Analogy, CauseEffect, Abduction, CounterFactual... |
| NLP | 5 | Tokenizer, NER, IntentClassifier, Sentiment, ContextTracker |
| Coding | 6 | Debug, Syntax, Logic, Algorithm, Security, Refactor |
| Neural | 3 | NeuralBridgeCell, SpikeInterpreter, StimulusDesigner |

### Knowledge Base (ships in repo)

78,063 entries in `luokai/data/knowledge.db` — no download:

| Category | Entries |
|---|---|
| Code conversations | 15,000 |
| Algorithms | 10,000 |
| Debugging scenarios | 10,000 |
| Security vulnerabilities | 8,000 |
| Architecture patterns | 8,000 |
| Code reviews, API patterns, test cases, CI/CD, DevOps, docs | 5,000 each |
| Deep Q&A (CSS, REST, Docker, ML, OAuth, JWT, recursion, Big O...) | 63 |

### Conversation Memory

All chats saved to `~/.luo_os/memory.json`. LUOKAI remembers context across sessions — last 10 turns injected into every new request. Clear from Settings → Privacy or `POST /api/memory/clear`.

---

## Browser — Headless Chromium

Every site works — Google, YouTube, Twitter, GitHub, everything.

```
User types URL → luo_server.py → Playwright/Chromium (headless)
                                       ↓
                            Chromium loads page fully (JS, cookies, sessions)
                                       ↓
                            Returns PNG screenshot + page HTML
                                       ↓
                            LuoOS displays pixel-perfect screenshot
```

**Install Chromium:** answered during setup wizard, or:
```bash
pip install playwright && python3 -m playwright install chromium
```

**Fallback:** urllib proxy works for static HTML sites if Chromium isn't installed.

---

## WorldMonitor (`apps/luo-worldmonitor`)

Cloned from [koala73/worldmonitor](https://github.com/koala73/worldmonitor). Integrated as a native LuoOS app.

10 live feed categories: **top · tech · finance · defense · science · climate · health · space · us · middle_east**

Ask LUOKAI about any headline directly from the feed. Click article → opens in Luo Browser.

---

## Neural Interface — Cortical Labs CL1

```python
from luokai.cells.neural import NeuralEngine

# Simulation mode (default — no hardware)
engine = NeuralEngine(sim_mode=True)
engine.start()

# Real CL1 hardware
engine = NeuralEngine(sim_mode=False, ticks_per_second=1000)
engine.start(try_hardware=True)

engine.stimulate_response("reward",    intensity=1.0)
engine.stimulate_response("reinforce", intensity=1.0)
```

Reads 64 MEA channels at 25kHz. Maps spike patterns to cognitive states. Feeds live visualizer in the dashboard.

---

## API

All at `http://localhost:3000`:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | Send message to LUOKAI (uses memory context) |
| GET | `/api/status` | System status + API keys |
| GET | `/api/brain/status` | Cell system status |
| POST | `/api/brain/learn` | Teach LUOKAI a fact |
| GET | `/api/model/status` | Local model ready/loading |
| GET | `/api/model/list` | Downloaded models |
| POST | `/api/config/key` | Save API key to config |
| GET | `/api/memory/history` | Chat history (last N turns) |
| POST | `/api/memory/clear` | Clear all memory |
| POST | `/api/browser/fetch` | Chromium-render any URL |
| POST | `/api/browser/search` | DuckDuckGo search |
| GET | `/api/browser/status` | Chromium engine ready? |
| GET | `/api/worldmonitor/feed` | Live news by category |
| POST | `/api/worldmonitor/multi` | Multiple categories at once |
| POST | `/api/fs/ls` | List directory |
| POST | `/api/fs/read` | Read file |
| POST | `/api/fs/write` | Write file |
| POST | `/api/fs/delete` | Delete file/folder |
| POST | `/api/fs/mkdir` | Create folder |
| POST | `/api/execute` | Run shell command (real bash) |

---

## File Structure

```
luo_os-v_0.1/
├── start.py               # One-click launcher — setup wizard on first run
├── setup_luoos.py         # First-run wizard (6 steps)
├── luo_server.py          # Flask backend (port 3000)
├── index.html             # Desktop UI (177KB — full OS in one file)
├── start.bat / start.sh   # Platform launchers
│
├── luokai/
│   ├── core/
│   │   ├── inference.py   # Inference engine — routing + generation
│   │   ├── model_engine.py # Local weights: download, load, generate
│   │   ├── brain.py       # CoEvo + KAIROS + TreeOfThought
│   │   ├── react_agent.py # ReAct agent
│   │   └── mind.py        # Core generation
│   │
│   ├── cells/
│   │   ├── base.py, reasoning.py, nlp.py, coding.py
│   │   ├── data_index.py  # SQLite knowledge search (thread-safe)
│   │   └── neural/        # CL1 MEA bridge, interpreter, stimulator
│   │
│   ├── data/
│   │   ├── knowledge.db   # 78,063 entries (12MB, ships in repo)
│   │   └── knowledge/     # k000.jsonl, k001.jsonl
│   │
│   ├── evolution/coevo.py
│   ├── skills/skills_library.py
│   └── voice/always_on.py
│
├── apps/
│   └── luo-worldmonitor/  # Cloned from koala73/worldmonitor
│
├── luo_agent/             # Autonomous agent subsystem
├── ai_core/               # Background AI systems
└── shell/luo_pkg.py       # Package manager
```

---

## Requirements

| | Value |
|---|---|
| Python | 3.6+ |
| RAM (no model) | 512MB |
| RAM (Qwen2.5 1.5B) | 2GB |
| RAM (Phi-3.5 mini) | 4GB |
| Disk | 1.5GB with model |
| GPU | Not required |
| Internet | First run only |

Auto-installed: `flask`, `flask-cors`, `llama-cpp-python`, `playwright`

---

## Roadmap

- [x] LUOKAI native AI — no external dependencies
- [x] 78K knowledge entries shipped in repo
- [x] Local AI weights (Qwen2.5 / Phi-3.5, auto-download)
- [x] Cortical Labs CL1 neural interface
- [x] First-run setup wizard
- [x] 60 API providers in setup
- [x] Headless Chromium browser (all sites)
- [x] WorldMonitor integration
- [x] Conversation memory (persists across sessions)
- [x] All apps working: VS Code, Browser, Files, Terminal, Notes, Music, Calculator, Calendar
- [x] Real file system API
- [x] Real shell terminal
- [ ] Voice interface activation
- [ ] Semantic search (vector embeddings)
- [ ] Multi-language support
- [ ] Packaged installer (PyInstaller .exe / .app)

---

*Built by Luo Kai — an OS that thinks.*
