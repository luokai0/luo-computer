# luo-computer

A self-contained AI agent operating system — built from scratch, zero external API dependencies.

```
cmake -B build && cmake --build build && ctest --test-dir build
```

## What it is

luo-computer is a C++17 library + server that runs a swarm of 10,000 AI agents
on your local machine. Agents plan tasks, operate a computer surface (browser,
terminal, windows), manage files and projects, and remember everything — all
without any cloud calls.

## Architecture

```
App (core) ──── Agents (10,000) ──── Tasks ──── Computer surface
    │                                               (browser/terminal/windows)
    ├── Memory store + Knowledge base
    ├── File manager + Project runner
    ├── Safety layer (RBAC, policies, approvals, kill switch)
    ├── Audit log + Privacy controls
    └── HTML dashboard (served locally)
```

## Features (100 steps complete)

| Area | What's built |
|------|-------------|
| **Auth** | Register, login, logout, session stages |
| **Agents** | 10k-agent swarm, skills, health, availability, inbox, kill switch |
| **Tasks** | Create, validate, tick, subtasks, priority, cancel, retry, filter |
| **Computer** | Browser snapshots, terminal history, window manager, undo |
| **LUO OS** | File tree indexer, search, persistence across restarts |
| **Memory** | Store, compress/summarize, search |
| **Knowledge** | KB entries, search, workspace snapshot export/import |
| **Files** | Upload, update, version history, rollback, diff, search |
| **Projects** | Add, run (3-phase: setup→run→teardown), template kinds |
| **Safety** | Approval gates, policy rules, RBAC, secret redaction, local-only mode |
| **Audit** | Append-only trace + audit log |
| **UI** | Full HTML dashboard: tabs, task inspector, agent grid, palette (⌘K) |
| **Search** | Universal search across all stores, ranked results |
| **Persistence** | TSV save/load, full round-trip verified |
| **CI** | GitHub Actions: Ubuntu/macOS/Windows × Debug/Release |
| **Packaging** | `scripts/package.sh`, `scripts/install.sh` |
| **Docs** | CHANGELOG, ARCHITECTURE, CONTRIBUTING, ROADMAP, PERFORMANCE |

## Build

```bash
# Requires: cmake ≥ 3.20, C++17 compiler
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

## Install

```bash
bash scripts/install.sh   # installs to ~/.local by default
PREFIX=/usr/local bash scripts/install.sh
```

## Dashboard

After starting the server, open `http://localhost:8080` in your browser.
Features: task inspector, agent roster, computer playback, file browser,
project runner, memory viewer, knowledge base, audit log, command palette (Ctrl+K).

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Performance](docs/PERFORMANCE.md)

## Project

GitHub: [luokai0/luo-computer](https://github.com/luokai0/luo-computer)
