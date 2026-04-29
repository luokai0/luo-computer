# LUO COMPUTER

LUO COMPUTER is the runtime where the LUO OS swarm works on a visible computer surface.

## What it does
- 3-6 letter usernames only
- Consent-first onboarding
- 10,000 seeded agents split into roles and expertise
- Tasks that decompose into visible steps
- A local computer record with browser / terminal / files / computer surfaces
- A visible action log so the user can watch what the swarm is doing
- A cloned `luo_os/` tree inside the repo that the swarm imports and works against
- Per-user secrets, files, skills, projects, and device links

## How it starts
- Click 1: launch `luo-computer`
- Click 2: inside the app, press **Start Session**

LUO OS is embedded inside the session workspace. It is not treated as a separate portable add-on.

## Current prototype
The app is a C++20 core with a generated HTML dashboard and deterministic state model.
It is cross-platform by design and stores its state in the user data directory.

## 100-step backlog to beat the current prototype

### Product foundation
- [x] 1. Replace the placeholder startup flow with a real end-to-end launch sequence.
- [x] 2. Add a true session state machine with idle, starting, running, paused, failed, and resumed states.
- [x] 3. Persist every user-visible action across restarts without losing the timeline.
- [ ] 4. Add a real multi-user boundary so each account is isolated by design.
- [x] 5. Make the onboarding flow explain exactly what the system can and cannot do.
- [x] 6. Add a first-run demo mode with sample agents, tasks, and computer activity.
- [x] 7. Add a user settings profile with import/export and reset.
- [x] 8. Add a proper home dashboard with summaries, shortcuts, and recent activity.
- [x] 9. Add a task creation flow with templates for research, coding, browsing, and ops.
- [ ] 10. Add a task history view with filters, search, and reopen/resume actions.

### Agent system
- [ ] 11. Replace synthetic seeded agents with real configurable agent records.
- [ ] 12. Add agent skills, reliability, availability, and cost metadata.
- [ ] 13. Add agent assignment logic based on role fit and current load.
- [ ] 14. Add agent handoff between steps instead of a single linear tick.
- [ ] 15. Add agent memory per task so agents can remember what they already saw.
- [ ] 16. Add agent-level approval gates for risky actions.
- [ ] 17. Add an agent inbox for instructions, responses, and follow-ups.
- [ ] 18. Add agent health checks and stuck-task detection.
- [ ] 19. Add parallel agent execution for independent subtasks.
- [ ] 20. Add an agent replay view so every decision can be audited.

### Computer surface
- [ ] 21. Replace the static computer log with a real interactive computer surface.
- [ ] 22. Add visible windows, tabs, and focus changes.
- [ ] 23. Add browser navigation with actual page snapshots.
- [ ] 24. Add terminal command execution with output capture.
- [ ] 25. Add file browsing with open, preview, rename, move, and delete.
- [ ] 26. Add copy-paste, drag-and-drop, and keyboard shortcut support.
- [ ] 27. Add screenshots and screen recording for every important action.
- [ ] 28. Add multi-monitor and multi-surface support.
- [ ] 29. Add a real computer playback timeline with scrubbing.
- [ ] 30. Add safe undo for supported computer actions.

### Planning and orchestration
- [ ] 31. Add a planner that breaks work into measurable steps automatically.
- [ ] 32. Add plan validation before execution starts.
- [ ] 33. Add dynamic replanning when a step fails or the environment changes.
- [ ] 34. Add subtask generation with dependencies and prerequisites.
- [ ] 35. Add execution budgets for time, steps, and risk.
- [ ] 36. Add task prioritization rules for urgent vs. long-running work.
- [ ] 37. Add queue management for many simultaneous tasks.
- [ ] 38. Add cancel, pause, resume, and retry controls.
- [ ] 39. Add deterministic replay for every task run.
- [ ] 40. Add completion scoring and confidence estimates.

### Memory and knowledge
- [ ] 41. Replace flat state storage with structured persistence.
- [ ] 42. Add durable chat and task memory per user.
- [ ] 43. Add long-term summaries that compress older activity.
- [ ] 44. Add search across files, tasks, logs, and memory.
- [ ] 45. Add embeddings or semantic retrieval for past work.
- [ ] 46. Add per-project memory scopes.
- [ ] 47. Add a knowledge base for instructions, rules, and reusable patterns.
- [ ] 48. Add import/export for memory and workspace snapshots.
- [ ] 49. Add provenance tracking for remembered facts.
- [ ] 50. Add conflict detection when memory entries disagree.

### Files, projects, and execution
- [ ] 51. Add a proper project runner with setup, run, and teardown phases.
- [ ] 52. Add sandboxed execution for user projects.
- [ ] 53. Add dependency detection and environment preparation.
- [ ] 54. Add logs, artifacts, and exit codes for every project run.
- [ ] 55. Add file diffing and patch preview before changes land.
- [ ] 56. Add version history and rollback for workspace files.
- [ ] 57. Add project templates for web, CLI, data, and automation tasks.
- [ ] 58. Add import support for zipped projects and repos.
- [ ] 59. Add package visibility and dependency summaries.
- [ ] 60. Add a workspace-wide search and indexing layer.

### Safety and trust
- [ ] 61. Keep consent boundaries explicit for every risky feature.
- [ ] 62. Add clear permission prompts before device, browser, or file access.
- [ ] 63. Add a kill switch that stops active agents instantly.
- [ ] 64. Add action-by-action logs the user can inspect.
- [ ] 65. Add secret redaction everywhere secrets might appear.
- [ ] 66. Add audit trails for all state changes.
- [ ] 67. Add role-based access control for multi-user scenarios.
- [ ] 68. Add policy checks for destructive or external actions.
- [ ] 69. Add a privacy dashboard showing exactly what is stored.
- [ ] 70. Add local-only mode with no external network calls by default.

### UI and UX
- [ ] 71. Redesign the UI so it feels finished, not prototype-like.
- [ ] 72. Add responsive layouts for desktop, tablet, and narrow windows.
- [ ] 73. Add search, filters, and keyboard navigation across the app.
- [ ] 74. Add clearer empty states, loading states, and failure states.
- [ ] 75. Add visual hierarchy for tasks, agents, memory, and computer state.
- [ ] 76. Add theme support and layout customization.
- [ ] 77. Add command palette / quick actions.
- [ ] 78. Add better typography, spacing, and iconography.
- [ ] 79. Add onboarding hints that teach the product by doing.
- [ ] 80. Add accessibility basics: contrast, focus states, and screen-reader labels.

### Competitive parity and beyond
- [ ] 81. Match OpenHands-level task execution quality for coding and repo editing.
- [ ] 82. Match Open Interpreter-level local control for files, terminal, and scripts.
- [ ] 83. Match Browser Use-level browser automation reliability.
- [ ] 84. Match Anthropic/OpenAI computer-use safety patterns with stronger human approval steps.
- [ ] 85. Match Agent S-style GUI autonomy with better replay and learning.
- [ ] 86. Add better benchmark coverage than any of the comparable projects.
- [ ] 87. Add public demo flows that prove the product in under 2 minutes.
- [ ] 88. Add reproducible showcase tasks with screenshots and logs.
- [ ] 89. Add docs that explain why this is better, not just what it is.
- [ ] 90. Add a clear open-source contribution path for outside collaborators.

### Release and growth
- [ ] 91. Add automated tests for every core subsystem.
- [ ] 92. Add integration tests for startup, task execution, and persistence.
- [ ] 93. Add CI that blocks regressions before merge.
- [ ] 94. Add packaging for macOS, Windows, Linux, and containerized use.
- [ ] 95. Add one-command install and one-command update flows.
- [ ] 96. Add release notes and changelog discipline.
- [ ] 97. Add telemetry only if it is opt-in and clearly explained.
- [ ] 98. Add performance profiling so the system stays fast as it grows.
- [ ] 99. Add a public roadmap with priorities, status, and owners.
- [ ] 100. Add a ruthless review cycle that keeps cutting anything mediocre.

## Working plan
- `file 'docs/luo-computer-10-step-plan.md'`
