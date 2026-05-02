# Changelog

All notable changes to luo-computer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Fixed
- **Data race (critical):** tick engine background thread now holds `workspace_mutex_` before
  calling `tick()` and `check_agent_health()`, preventing concurrent writes with the HTTP
  server thread. Removed the broken `auto_save_` toggle workaround that was silently
  dropping saves during background ticks.
- **Server crash on bad input:** `POST /api/tasks` (priority param), `POST /api/tasks/:id/priority`,
  and `POST /api/files/:name/rollback` all called `std::stoi`/`std::stoul` without try/catch.
  A non-numeric value in any of these params would throw and crash the whole server process.
  All three handlers are now guarded with try/catch and fall back to safe defaults.
- **State load crash on corrupt file:** `stoll`, `stoull`, and `stoi` calls in `load_workspace`
  and `load_global` now wrapped in try/catch. A single corrupt or truncated line in the
  persistence file no longer crashes startup; the bad record is skipped and loading continues.

### Added (Steps 1-100)

#### Core & Auth
- `App` class with full user registration, login, logout, session state
- `ConsentFlags` struct with granular privacy controls
- `local_only_mode` — no outbound network calls when enabled
- `export_user_settings` / `import_user_settings`
- `reset_workspace` — wipe and start fresh

#### Session Management (Steps 1-4)
- `start_session`, `resume_session`, `pause_session`, `fail_session`
- `SessionStage` enum: Idle → Starting → Running → Paused → Failed → Resumed
- Session persistence across restarts via `StateIO`

#### LUO OS Index (Steps 1, 9)
- `import_luo_os` — walk source tree and build in-memory index
- `rebuild_luo_index` — restore index from persisted root path on load
- `search_luo_os` — substring search across all indexed entries
- `luo_index_entries` — paginated access to index

#### Agents (Steps 6, 12-20)
- `AgentProfile` with skills, load, health, availability, reliability
- `AgentSkill` struct: name, level, domain
- 10,000-agent default swarm with role distribution
- `update_agent_skills`, `set_agent_availability`
- `filter_agents` — filter by role, expertise, busy state, task assignment
- `send_agent_message` / `add_agent_message` / `agent_messages`
- `kill_all_agents` — emergency kill switch stops all agents instantly
- Agent health tracking: ok / degraded / stuck

#### Tasks (Steps 9, 31-40)
- `create_task` with title, description, kind, priority (1-10)
- `validate_task` — check plan completeness before execution
- `tick` — advance running tasks through plan steps
- `reopen_task`, `resume_task`, `cancel_task`, `pause_task`
- `retry_task_step` — rewind step cursor and re-run
- `set_task_priority`
- `add_subtask` with dependency chains
- `tasks_filtered` — filter by status, kind, full-text search
- `get_task` — optional lookup by id
- `TaskStep` extended: status, agent_id, output fields
- `SubTask` with depends_on list

#### Computer Surface (Steps 21-30)
- `attach_computer`, `set_active_computer`
- `open_window`, `close_window`, `focus_window`
- `navigate_browser` — captures URL, title, text excerpt
- `run_terminal_command` — captures command, output, exit code
- `undo_computer_action` — mark last action as undone
- `browser_history`, `terminal_history` accessors
- `ComputerAction` extended: undone flag, undo_detail

#### Memory & Knowledge (Steps 41-50)
- `add_memory` with kind, content, source, tags
- `summarize_old_memories` — compress old entries into summaries
- `search_memory` — substring search across memory store
- `add_knowledge`, `search_knowledge`, `knowledge_entries`
- `export_workspace_snapshot` — write files + knowledge to disk
- `import_workspace_snapshot` — load files from directory

#### Files & Projects (Steps 51-60)
- `upload_file` with project_scope; auto-updates if name exists
- `update_file` with automatic version history
- `rollback_file` to any previous version
- `diff_file` — compute old vs new patch
- `search_files` — search by name or content
- `add_project` with template_kind: web, cli, data, automation
- `run_project` — three-phase runner: setup → run → teardown
- `approve_device`, device permission levels

#### Safety & Trust (Steps 61-70)
- `require_approval` / `approve_action` — action gating
- `add_policy` / `check_policy` — deny/allow/require rules
- `set_user_role` / `user_role` / `user_can` — RBAC (admin/operator/viewer)
- `redact_secrets` — strip secret values from any string
- `set_local_only_mode` — enforce zero outbound calls
- `audit_log` — append-only audit trail
- `add_trace` — structured trace events

#### Universal Search (Steps 44, 60, 73)
- `search_all` — ranked search across tasks, files, memory,
  knowledge, agents, audit log

#### UI / Dashboard (Steps 71-80)
- Full single-file HTML dashboard via `render_dashboard_html`
- CSS design system: dark theme, tokens, responsive grid
- Topbar with session stage, platform, local-only indicator
- Summary stat cards (9 metrics)
- Tab navigation: Overview, Agents, Computer, Files, Projects,
  Memory, Audit
- Task inspector with live JSON-driven plan timeline
- Task history with status/kind/text filters
- Agent roster grid with health indicators
- Computer playback timeline with undo markers
- Browser history and terminal history panels
- File browser table with version count
- Project runner with phase output
- Memory viewer with summarized markers
- Knowledge base panel
- Audit log panel
- Devices panel
- Privacy/consent dashboard
- Pending approvals banner
- Command palette (Ctrl+K) with keyboard navigation
- ARIA roles and labels throughout (accessibility)
- `render_status_html` — plain-text health endpoint

#### Tests (Steps 91-92)
- 100+ assertions across all subsystems
- Named sections with PASS/FAIL reporting
- Performance baseline: 100 tasks + 50 searches + 200 memories < 5s
- Persistence round-trip: save → reload → verify all fields

#### CI (Step 93)
- GitHub Actions: Ubuntu 24, macOS 14, Windows 2022
- Debug and Release matrix
- clang-tidy static analysis job

#### Packaging (Steps 94-95)
- `scripts/package.sh` — cross-platform release archive builder
- `scripts/install.sh` — one-line installer

#### Docs (Steps 96-100)
- `CHANGELOG.md` (this file)
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTRIBUTING.md`

### Fixed (Bug fixes from initial audit)
- `AgentMessage` declared after `Workspace` that uses it — moved before
- `session_stage_to_string/from_string` defined in both header and
  `app.cpp` anonymous namespace — removed duplicates from header
- `rowify()` rejected brace-init lists — added `initializer_list` overload
- `logout()`, `authenticated()`, `current_user()` missing from public API
- `global_state_file()` accessed private `data_root_`
- `state_store.cpp` called non-existent `app.active_user()`
- `startup.hpp` used `std::cin`/`cout` with only `<iosfwd>`
- `startup.cpp` missing `server.hpp` include for `run_server`
- `confirm()` called `std::transform` on `const` string iterators
- `record_trace()` called from outside class (private)
- `append_task_history()` used before definition — forward declaration
- LUO OS index lost on reload — `rebuild_luo_index()` added

---

## [0.1.0] — Initial scaffold
- Repository created with CMake build system
- Basic `App`, `StateIO`, `Startup`, `Server`, `UI` skeletons
- `luo_os` source tree structure
- Initial test harness
