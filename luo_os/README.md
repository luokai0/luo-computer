# LuoOS — The AI-Native Operating System

> **Built by Luo Kai.** An OS where the AI *is* the system — not a plugin, not a feature.

LUOKAI is the brain of LuoOS. It runs 100% locally — no Ollama, no OpenAI, no cloud. Run it and it works.

---

## Quick Start

```bash
git clone https://github.com/luokai25/luo_os-v_0.1.git
cd luo_os-v_0.1
python3 start.py        # or double-click start.bat on Windows
```

Opens at `http://localhost:3000`. On first run a setup wizard guides you through everything — model choice, theme, API keys, and more. Takes about 60 seconds. Never runs again unless you reset it.

---

## How to Run

| Method | Command |
|---|---|
| Windows | Double-click `start.bat` |
| Mac / Linux | `./start.sh` |
| Any Python 3.6+ | `python3 start.py` |
| GitHub Codespaces | Open repo → Code → Codespaces → `python3 start.py` |
| Docker | `docker run -p 3000:3000 -v ~/.luo_os:/root/.luo_os luokai25/luo_os` |
| pip | `pip install luo-os && luo-os start` |
| Replit | Import from GitHub → Run |
| Gitpod | `https://gitpod.io/#https://github.com/luokai25/luo_os-v_0.1` |
| VS Code Dev Container | Open folder → "Reopen in Container" |
| Linux server | `python3 luo_server.py` (headless) |

---

## First-Run Setup Wizard

`setup_luoos.py` runs automatically on first launch. Six steps:

**Step 1 — Name.** Type your name. LUOKAI uses it in every greeting.

**Step 2 — AI Model.** The wizard reads your RAM and recommends:
- Under 4GB RAM → Qwen2.5 1.5B (900MB, downloads once)
- 4–8GB RAM → Qwen2.5 3B (1.8GB)
- 8GB+ RAM → Phi-3.5 mini (2.2GB, best quality)
- No download → cell system only (still answers most things instantly)

**Step 3 — Appearance.** Five themes (Dark, Darker, Hacker, Ocean, Light) and four wallpaper styles. CSS variables injected into `index.html` on save.

**Step 4 — API Keys.** Optionally connect 60 external services grouped by category. All stored in `~/.luo_os/config.json` — local only.

**Step 5 — Features.** Toggle voice, co-evolution engine, neural interface, auto-learn, VS Code integration independently.

**Step 6 — Startup.** Port, auto-open browser, show tips.

Reset at any time: `python3 setup_luoos.py --reset`

---

## LUOKAI Brain

```
┌─────────────────────────────────────────────────────────┐
│                      LUOKAI BRAIN                       │
│                                                         │
│  Routing (fastest → slowest):                           │
│  1. Identity / math / greet       → instant             │
│  2. Coding cells (debug/algo)     → instant             │
│  3. Knowledge DB (78K entries)    → instant             │
│  4. Local model (Qwen2.5/Phi)     → ~1–3s               │
│  5. Skills library (4,146)        → instant             │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Reasoning  │  │     NLP     │  │   Coding    │     │
│  │  14 cells   │  │   5 cells   │  │   6 cells   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │        Knowledge Base  —  78,063 entries         │   │
│  │  algorithms · debug · security · APIs · devops   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │    Local AI Weights — Qwen2.5 / Phi-3.5          │   │
│  │  Downloads once (~900MB–2.2GB) · CPU only        │   │
│  │  Runs fully offline after first download         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │       Neural Interface — Cortical Labs CL1       │   │
│  │  64-channel MEA · spike detection · stimulation  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Cell System

| Family | Cells | Description |
|---|---|---|
| Reasoning | 14 | ModusPonens, Syllogism, Analogy, CauseEffect, Abduction, CounterFactual, BestExplanation... |
| NLP | 5 | Tokenizer, NER, IntentClassifier, Sentiment, ContextTracker |
| Coding | 6 | Debug, Syntax, Logic, Algorithm, Security, Refactor |
| Neural | 3 | NeuralBridgeCell, SpikeInterpreter, StimulusDesigner |

### Knowledge Base

78,063 curated entries in `luokai/data/knowledge.db` (ships in repo, no download):

| Category | Entries |
|---|---|
| Code conversations | 15,000 |
| Algorithms | 10,000 |
| Debugging scenarios | 10,000 |
| Security vulnerabilities | 8,000 |
| Architecture patterns | 8,000 |
| Code reviews, API patterns, test cases, CI/CD, DevOps, documentation | 5,000 each |
| Deep Q&A (CSS, REST, Docker, ML, OAuth, JWT, recursion, Big O...) | 53 |

---

## Desktop — Two UIs

### Classic Desktop (`/` or `/classic`)
Traditional windowed OS layout. Apps, taskbar, file manager, code editor, terminal, browser, AI chat.

### 3D Spatial Desktop (`/3d`)
Four floating screens in 3D space:
- **LUOKAI Chat** — full AI conversation
- **Code Editor** — syntax-highlighted, line numbers
- **Dashboard** — live metrics (spikes, skills, model, uptime, response time)
- **Neural MEA** — 64-channel real-time spike visualizer

3D interactions:
- Mouse moves → world tilts ±4° horizontal, ±2.5° vertical
- Drag any titlebar → move screen anywhere
- Scroll wheel → zoom the whole world
- Double-click titlebar → maximize/restore
- Right-click → context menu
- Ctrl+1/2/3/4 → toggle screens · Ctrl+T → tile all · Ctrl+R → reset

Switch at any time in Settings → Appearance → UI Mode, or navigate directly to `/3d` or `/classic`.

---

## Settings (fully working)

Open Settings from the taskbar icon or by opening the Settings app. Eight tabs:

| Tab | What you can do |
|---|---|
| **Appearance** | Dark mode, shadows, animations, blur, font size, UI mode (classic/3D) |
| **LUOKAI AI** | Voice toggle, co-evolution, auto-learn, neural engine selector, live model status |
| **Voice** | Enable/disable, wake word, speed, test voice |
| **Evolution** | Enable co-evolution, mutation rate, learning speed, start cycle |
| **API Keys** | Enter keys for OpenAI, Anthropic, GitHub, Stripe, Twilio, SendGrid, AWS, Cloudflare, and 9 more — saved locally |
| **Themes** | Six themes with live preview: Dark, Darker, Hacker, Ocean, Light, Purple |
| **System** | OS version, skills count, knowledge DB size, model status, GitHub link |
| **Privacy** | Local-only mode, save history, telemetry (all off by default), clear history |
| **Network** | Port, server status, LAN access toggle, API URL |

---

## Neural Interface — Cortical Labs CL1

```python
from luokai.cells.neural import NeuralEngine

# Simulation mode (runs without hardware)
engine = NeuralEngine(sim_mode=True)
engine.start()

# Real CL1 hardware
engine = NeuralEngine(sim_mode=False, ticks_per_second=1000)
engine.start(try_hardware=True)

# Send stimulation based on AI state
engine.stimulate_response("reward",    intensity=1.0)
engine.stimulate_response("reinforce", intensity=1.0)
engine.stimulate_response("explore",   intensity=0.8)
```

Stimulation presets: `reward` (5×50Hz), `reinforce` (10×100Hz), `explore` (2×10Hz), `error` (1× mild), `probe`, `reset`, `entrain_theta`, `entrain_gamma`.

Spike patterns → cognitive states: FOCUSED, ENGAGED, ANALYTICAL_FOCUS, CREATIVE_FOCUS, RESTING, SYNCHRONIZED.

---

## API

All endpoints at `http://localhost:3000`:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | Send message to LUOKAI |
| GET | `/api/status` | System status + API keys list |
| GET | `/api/brain/status` | Cell system status |
| POST | `/api/brain/learn` | Teach LUOKAI a fact |
| GET | `/api/model/status` | Local model ready/loading/error |
| GET | `/api/model/list` | Available downloaded models |
| POST | `/api/config/key` | Save an API key to config |
| GET | `/api/skills` | List all skills |
| GET | `/api/skills/stats` | Skill statistics |
| POST | `/api/execute` | Run Python code |
| GET | `/api/voice/status` | Voice engine status |
| POST | `/api/voice/start` | Start always-on voice |
| POST | `/api/voice/stop` | Stop voice |
| POST | `/api/evolution/start` | Start co-evolution cycle |
| GET | `/api/evolution/stats` | Evolution statistics |
| POST | `/api/fs/ls` | List directory |
| POST | `/api/fs/read` | Read file |
| POST | `/api/fs/write` | Write file |

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is binary search?"}'
```

---

## File Structure

```
luo_os-v_0.1/
├── start.py                   # One-click launcher — runs setup wizard first
├── setup_luoos.py             # First-run setup wizard (6 steps)
├── luo_server.py              # Flask backend (port 3000)
├── index.html                 # Classic desktop UI
├── index_3d.html              # 3D spatial desktop UI
├── start.bat / start.sh       # Platform launchers
│
├── luokai/
│   ├── core/
│   │   ├── inference.py       # Main inference engine — routing + generation
│   │   ├── model_engine.py    # Local model: download, load, generate
│   │   ├── brain.py           # Brain: CoEvo + KAIROS + TreeOfThought
│   │   ├── react_agent.py     # ReAct agent with planning + reflection
│   │   ├── luokai_agent.py    # Full agent with voice + memory
│   │   └── mind.py            # Core generation (called by react_agent)
│   │
│   ├── cells/
│   │   ├── base.py            # BaseCell (id, state, connections, learn)
│   │   ├── reasoning.py       # 14 reasoning cells + ReasoningEngine
│   │   ├── nlp.py             # 5 NLP cells + NLPEngine
│   │   ├── coding.py          # 6 coding cells + CodingEngine
│   │   ├── data_index.py      # SQLite knowledge search (thread-safe)
│   │   └── neural/
│   │       ├── bridge.py      # NeuralBridgeCell — CL1 MEA interface
│   │       ├── interpreter.py # Spike patterns → cognitive states
│   │       └── stimulator.py  # LUOKAI decisions → electrode stimulation
│   │
│   ├── data/
│   │   ├── knowledge.db       # 78,063 entries (12MB SQLite, in repo)
│   │   ├── knowledge/
│   │   │   ├── k000.jsonl     # Base 78K entries
│   │   │   └── k001.jsonl     # Deep Q&A (CSS, REST, Docker, ML...)
│   │   └── build_knowledge.py # Knowledge builder script
│   │
│   ├── evolution/
│   │   ├── coevo.py           # Co-evolution engine
│   │   └── benchmarks.py      # Performance benchmarks
│   │
│   ├── skills/
│   │   └── skills_library.py  # 4,146 skills across 20 domains
│   │
│   └── voice/
│       └── always_on.py       # Always-on voice interface
│
├── luo_agent/                 # Autonomous agent subsystem
│   ├── core/
│   │   ├── llm.py             # LUOKAI HTTP shim (OllamaClient compat)
│   │   ├── config.py          # Agent configuration
│   │   └── daemon.py          # Background agent daemon
│   ├── agents/agent.py        # Agent implementation
│   ├── memory/                # Memory: cells, vectors, persistence
│   ├── orchestration.py       # Multi-agent orchestration
│   └── ui/                    # TUI + terminal UI
│
├── ai_core/                   # Background AI systems
│   ├── kairos.py              # KAIROS proactive agent
│   ├── daemon.py              # AI core daemon
│   └── search.py              # Web search integration
│
├── apps/                      # Built-in OS apps
│   ├── browser.py             # Web browser
│   ├── file_manager.py        # File manager
│   └── text_editor.py         # Text editor
│
├── ui/
│   ├── window_manager.py      # Tkinter window manager (desktop mode)
│   └── dashboard.html         # System dashboard
│
└── shell/
    └── luo_pkg.py             # Package manager
```

---

## Requirements

| Requirement | Value |
|---|---|
| Python | 3.6+ |
| RAM (cells only, no model) | 512MB |
| RAM (with Qwen2.5 1.5B) | 2GB |
| RAM (with Phi-3.5 mini) | 4GB |
| Disk | 1.5GB (with model) |
| GPU | Not required — CPU only |
| Internet | First run only (model download) |

Auto-installed: `flask`, `flask-cors`, `llama-cpp-python`

---

## Roadmap

- [x] LUOKAI native AI — no external dependencies
- [x] Cell system — reasoning, NLP, coding, neural (25 cells)
- [x] 78K knowledge entries shipped in repo
- [x] Local AI weights — Qwen2.5 1.5B / 3B / Phi-3.5 mini
- [x] Cortical Labs CL1 neural interface
- [x] First-run setup wizard (6 steps)
- [x] 60 API providers in setup
- [x] Classic desktop UI + 3D spatial desktop UI
- [x] Settings with 9 fully working tabs
- [x] One-click start (Windows / Mac / Linux)
- [x] Python 3.6+ compatibility
- [ ] Persistent conversation memory
- [ ] Voice-first interface
- [ ] Multi-language support
- [ ] Plugin system for custom cells

---

*Built by Luo Kai — an OS that thinks.*
