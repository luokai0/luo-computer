"""
luo_os — Luo OS Python runtime, embedded in luo-computer.

Source: github.com/luokai25/luo_os-v_0.1
Author: Luo Kai (luokai25 / luokai0)

This package contains the full Luo OS AI stack:
  luo_agent/   — multi-agent orchestration, memory cells (Luo Cells), tools
  luokai/      — LUOKAI native AI engine: brain, cells, inference, react agent,
                 self-improve, MCP integration, voice, evolution, skill library
  ai_core/     — KAIROS proactive daemon, daemon, memory, multi_agent, search
  apps/        — browser, file_manager, text_editor

Entry points callable by luo-computer's run_project system:
  python3 -m luo_os.luo_server    — start REST/agent API servers
  python3 -m luo_os.ai_core.kairos start  — start KAIROS background daemon
  python3 -m luo_os.luo_cli      — interactive CLI
"""
