# Architecture

## Overview

```
luo-computer/
├── include/luo_gate/     # Public headers (API surface)
│   ├── app.hpp           # Core App class — all business logic
│   ├── luo_index.hpp     # LUO OS file indexer
│   ├── security.hpp      # Username/password validation, hashing
│   ├── state_io.hpp      # Raw TSV read/write for persistence
│   ├── state_store.hpp   # High-level save/load orchestration
│   ├── startup.hpp       # CLI onboarding flow
│   ├── server.hpp        # HTTP server (serve dashboard)
│   ├── platform.hpp      # OS detection, paths
│   └── ui.hpp            # HTML dashboard renderer
├── src/                  # Implementations
├── tests/                # Test suite (app_tests.cpp)
├── docs/                 # Documentation
├── scripts/              # Build/package helpers
└── luo_os/               # LUO OS source tree (indexed at runtime)
```

## Core Data Flow

```
User → StartupFlow → App → StateIO → Disk
              ↓
           Server → render_dashboard_html → Browser
              ↓
           Tick loop → AgentProfile → TaskRecord → ComputerAction
```

## Key Design Decisions

### Single-header API (`app.hpp`)
All types and the `App` class are declared in one header. This makes
it easy to include from server, UI, tests, and CLI without circular
dependency issues.

### Workspace per user
Every authenticated user gets their own `Workspace` struct stored in
`workspaces_[username]`. This makes multi-user support natural without
shared mutable state.

### TSV persistence
State is stored as tab-separated values rather than JSON/SQLite:
- No external parser dependency
- Human-readable and diff-friendly
- Fast sequential write on save

### Stateless renderer
`render_dashboard_html` is a pure function of `const App&`. The
dashboard is rendered fresh on every request. Interactive state
lives in the browser via embedded `<script>` blocks.

### Agent swarm model
Agents are lightweight value types in a `vector<AgentProfile>`.
The swarm seeds 10,000 agents at login. `tick()` assigns the best
available agent to each running task step using `find_best_agent`.

### Memory compression
Old memory entries are summarized in-place by `summarize_old_memories`
to keep the store bounded. Summarized entries are flagged and excluded
from main retrieval but kept for audit.

### Safety layers (defence in depth)
1. `local_only_mode` — no outbound calls
2. `require_approval` — gate destructive actions
3. `check_policy` — deny rules evaluated before execution
4. `user_can` — RBAC: admin / operator / viewer
5. `redact_secrets` — strip secrets before logging or display
6. `kill_all_agents` — emergency stop
