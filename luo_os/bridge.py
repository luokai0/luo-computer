#!/usr/bin/env python3
"""
luo_os/bridge.py — luo-computer ↔ luo_os integration bridge.

Called by luo-computer's C++ run_project system as a subprocess.
Commands:
  python3 bridge.py status           — JSON status of all luo_os subsystems
  python3 bridge.py start [service]  — start a service (server|kairos|all)
  python3 bridge.py stop  [service]  — stop a service
  python3 bridge.py chat  <message>  — send message to luo_os AI, print response
  python3 bridge.py memory stats     — JSON memory statistics
  python3 bridge.py memory recall    — last 5 memory entries as JSON
  python3 bridge.py agents list      — JSON list of running agents
  python3 bridge.py kairos status    — KAIROS daemon status
  python3 bridge.py kairos task <t>  — queue a task in KAIROS
  python3 bridge.py skills list      — list available skill categories

All output is valid JSON for easy parsing by the C++ side.
"""

import sys
import os
import json
import subprocess
import socket
from pathlib import Path
from datetime import datetime

# Add luo_os package root to path
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))  # luo-computer root
sys.path.insert(0, str(_HERE))         # luo_os root


def _json(obj):
    print(json.dumps(obj, indent=2, default=str))


def _port_open(port: int) -> bool:
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False


# ── status ────────────────────────────────────────────────────────────────────
def cmd_status():
    # Memory stats
    mem_stats = {}
    try:
        from luo_os.ai_core.memory import stats as mem_stats_fn
        mem_stats = mem_stats_fn()
    except Exception as e:
        mem_stats = {"error": str(e)}

    # KAIROS state
    kairos_state = {}
    kairos_state_file = Path("~/.luo_os/kairos_state.json").expanduser()
    if kairos_state_file.exists():
        try:
            kairos_state = json.loads(kairos_state_file.read_text())
        except Exception:
            pass

    # Skill library
    skill_cats = []
    skill_dir = _HERE / "luokai" / "skills" / "library"
    if skill_dir.exists():
        skill_cats = sorted(d.name for d in skill_dir.iterdir() if d.is_dir())

    _json({
        "luo_os_version": "0.1",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "agent_api":  _port_open(7070),
            "rest_api":   _port_open(7071),
            "luokai_llm": _port_open(3000),
        },
        "memory": mem_stats,
        "kairos": kairos_state,
        "skill_categories": len(skill_cats),
        "packages": {
            "luo_agent":  (_HERE / "luo_agent").exists(),
            "luokai":     (_HERE / "luokai").exists(),
            "ai_core":    (_HERE / "ai_core").exists(),
            "apps":       (_HERE / "apps").exists(),
        }
    })


# ── memory ────────────────────────────────────────────────────────────────────
def cmd_memory(args):
    sub = args[0] if args else "stats"
    try:
        from luo_os.ai_core.memory import stats, recall, get_all_facts
        if sub == "stats":
            _json(stats())
        elif sub == "recall":
            query = args[1] if len(args) > 1 else None
            _json(recall(query=query, limit=10))
        elif sub == "facts":
            _json(get_all_facts())
        else:
            _json({"error": f"unknown memory subcommand: {sub}"})
    except Exception as e:
        _json({"error": str(e)})


# ── agents ────────────────────────────────────────────────────────────────────
def cmd_agents(args):
    sub = args[0] if args else "list"
    if sub == "list":
        try:
            from luo_os.ai_core.multi_agent import LuoAgentManager
            mgr = LuoAgentManager()
            _json(mgr.list_agents())
        except Exception as e:
            _json({"error": str(e)})


# ── kairos ────────────────────────────────────────────────────────────────────
def cmd_kairos(args):
    sub = args[0] if args else "status"
    if sub == "status":
        state_file = Path("~/.luo_os/kairos_state.json").expanduser()
        alerts_file = Path("~/.luo_os/kairos_alerts.json").expanduser()
        state = {}
        alerts = []
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except Exception:
                pass
        if alerts_file.exists():
            try:
                raw = json.loads(alerts_file.read_text())
                alerts = [a for a in raw if not a.get("read")]
            except Exception:
                pass
        _json({"state": state, "unread_alerts": alerts})
    elif sub == "task":
        task_text = " ".join(args[1:])
        if not task_text:
            _json({"error": "task text required"}); return
        try:
            from luo_os.ai_core.kairos import KAIROS
            k = KAIROS()
            k.queue_task(task_text)
            _json({"ok": True, "task": task_text})
        except Exception as e:
            _json({"error": str(e)})
    elif sub == "alerts":
        alerts_file = Path("~/.luo_os/kairos_alerts.json").expanduser()
        try:
            alerts = json.loads(alerts_file.read_text()) if alerts_file.exists() else []
            _json(alerts[-20:])
        except Exception as e:
            _json({"error": str(e)})


# ── chat ──────────────────────────────────────────────────────────────────────
def cmd_chat(args):
    message = " ".join(args)
    if not message:
        _json({"error": "message required"}); return
    # Try luo_agent first, fall back to simple echo
    try:
        from luo_os.luo_agent.luo_agent import LuoAgent
        agent = LuoAgent()
        response = agent.chat(message)
        _json({"response": response, "agent": "luo_agent"})
    except Exception as e1:
        # Fall back to multi_agent
        try:
            from luo_os.ai_core.multi_agent import LuoAgentManager
            mgr = LuoAgentManager()
            result = mgr.root.think(message)
            _json({"response": result, "agent": "multi_agent"})
        except Exception as e2:
            _json({"error": f"luo_agent: {e1}, multi_agent: {e2}"})


# ── skills ────────────────────────────────────────────────────────────────────
def cmd_skills(args):
    sub = args[0] if args else "list"
    skill_dir = _HERE / "luokai" / "skills" / "library"
    if sub == "list":
        if not skill_dir.exists():
            _json({"error": "skill library not found"}); return
        cats = sorted(d.name for d in skill_dir.iterdir() if d.is_dir())
        _json({"categories": cats, "count": len(cats)})
    elif sub == "get" and len(args) > 1:
        # Find category matching keyword
        keyword = args[1].lower()
        if not skill_dir.exists():
            _json({"error": "skill library not found"}); return
        for cat in skill_dir.iterdir():
            if keyword in cat.name.lower():
                files = [f.name for f in cat.rglob("*") if f.is_file()][:20]
                _json({"category": cat.name, "files": files, "count": len(files)})
                return
        _json({"error": f"no skill category matching '{keyword}'"})


# ── start/stop ────────────────────────────────────────────────────────────────
def cmd_start(args):
    service = args[0] if args else "all"
    results = {}
    if service in ("server", "all"):
        try:
            proc = subprocess.Popen(
                [sys.executable, str(_HERE / "luo_server.py")],
                cwd=str(_HERE),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            results["server"] = {"pid": proc.pid, "status": "started"}
        except Exception as e:
            results["server"] = {"error": str(e)}
    if service in ("kairos", "all"):
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "luo_os.ai_core.kairos", "start"],
                cwd=str(_HERE.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            results["kairos"] = {"pid": proc.pid, "status": "started"}
        except Exception as e:
            results["kairos"] = {"error": str(e)}
    _json(results)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args:
        cmd_status(); return

    cmd = args[0]
    rest = args[1:]

    dispatch = {
        "status":  lambda: cmd_status(),
        "memory":  lambda: cmd_memory(rest),
        "agents":  lambda: cmd_agents(rest),
        "kairos":  lambda: cmd_kairos(rest),
        "chat":    lambda: cmd_chat(rest),
        "skills":  lambda: cmd_skills(rest),
        "start":   lambda: cmd_start(rest),
    }

    fn = dispatch.get(cmd)
    if fn:
        fn()
    else:
        _json({"error": f"unknown command: {cmd}", "commands": list(dispatch.keys())})


if __name__ == "__main__":
    main()
