# Luo OS — System Architecture
*Built by Abd El-Rahman Abbas (Mr. Kai)*

---

## Overview
```
┌─────────────────────────────────────────────────────────┐
│                     USER / AI AGENT                     │
├─────────────────────────────────────────────────────────┤
│  Luo Shell      │  Desktop GUI    │  REST API :8080     │
├─────────────────────────────────────────────────────────┤
│              Luo Agent (Autonomous AI)                  │
│   memory/  │  tools/  │  agents/  │  ui/  │  daemon     │
├─────────────────────────────────────────────────────────┤
│                    AI Core Layer                        │
│  agent_identity  │  agent_api :7070  │  multi_agent     │
├─────────────────────────────────────────────────────────┤
│            Package Manager │ App Store │ Compat         │
├─────────────────────────────────────────────────────────┤
│              Kernel (Linux + Redox + XNU)               │
└─────────────────────────────────────────────────────────┘
```

---

## Layers

### 1. Kernel Layer
- Linux base — hardware drivers, process management, filesystem
- Redox OS (Rust) — experimental microkernel components
- XNU Mach — IPC and message passing concepts
- Location: `kernel/`

### 2. AI Core Layer
- **agent_identity.py** — auto-provisions unique identity for any AI agent
- **agent_api.py** — socket API on port 7070, token-authenticated
- **rest_api.py** — HTTP REST API on port 8080
- **multi_agent.py** — spawn and coordinate multiple sub-agents
- **daemon.py** — always-on local AI process
- Location: `ai_core/`

### 3. Luo Agent
- Autonomous AI agent powered by LUOKAI native inference (local, free, offline)
- **core/** — config, LUOKAI inference, background daemon
- **memory/** — MEMORY.md + notes + autoDream consolidation
- **tools/** — 14 permission-gated tools
- **agents/** — reasoning loop with automatic tool calling
- **ui/** — colored streaming terminal
- Location: `luo_agent/`

### 4. Shell Layer
- **luo_shell.sh** — interactive shell with built-in OS commands
- **luo_pkg.py** — package manager (35+ packages, 8 categories)
- Location: `shell/`

### 5. UI Layer
- **window_manager.py** — Python/tkinter desktop GUI
- **dashboard.html** — web-based control panel
- Location: `ui/`

### 6. Apps
- text_editor, browser, file_manager
- Location: `apps/`

### 7. Compat
- **wine_bridge.py** — run Windows .exe files
- Location: `compat/`

---

## Agent Identity System
```
fingerprint = sha256(hostname + platform + agent_name + model)
agent_id    = "luo_" + fingerprint[:16]
api_token   = uuid4()
```

Identity persisted in `~/.luo_os/agent_registry.json`.
Same agent on same machine always gets same ID.
Each agent gets: memory dir, notes dir, sessions dir, config file.

---

## Memory Architecture (Luo Agent)
```
MEMORY.md     short facts, always loaded (< 5KB)
notes/        detailed notes, loaded on demand
sessions/     full conversation history, searched selectively
```

autoDream runs every 10 daemon ticks — consolidates MEMORY.md,
removes duplicates and contradictions, converts vague notes to facts.

---

## Tool System

| Tool | Permission | Description |
|---|---|---|
| read_file | no | Read file |
| write_file | yes | Write file |
| append_file | yes | Append to file |
| list_dir | no | List directory |
| delete_file | yes | Delete file |
| move_file | yes | Move/rename |
| file_exists | no | Check existence |
| bash | yes | Shell command |
| web_search | no | DuckDuckGo |
| fetch_url | no | Fetch URL |
| run_python | yes | Run Python |
| get_datetime | no | Current time |
| get_env | no | Env variable |
| system_info | no | System info |

---

## Multi-Agent Architecture
```
LuoCoordinator (root)
├── LuoSubAgent: Researcher
├── LuoSubAgent: Builder
├── LuoSubAgent: Reviewer
└── LuoSubAgent: Monitor
```

---

## Boot Sequence
```
python3 luo_init.py
    ├── 1. Identity Registry
    ├── 2. Agent API :7070
    ├── 3. REST API  :8080
    └── 4. Luo Agent Daemon
```

*Part of Luo OS v0.1 — open source forever*
