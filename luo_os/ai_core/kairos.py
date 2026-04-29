import threading
import json
#!/usr/bin/env python3
"""
Luo OS — KAIROS Mode
=====================
Always-on proactive agent. Runs in background, acts without being asked.
Watches files, monitors system, queues tasks, sends alerts.

Inspired by Claude Code leak architecture concept — clean-room implementation.
Author: Abd El-Rahman Abbas (Mr. Kai) — Luo OS
"""

import os, sys, json, time, threading, subprocess, hashlib
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "luo_agent"))

from core.config import LuoConfig

from memory.memory import MemorySystem

# ── Config ────────────────────────────────────────────────────────────
KAIROS_LOG   = Path("~/.luo_os/kairos.log").expanduser()
KAIROS_STATE = Path("~/.luo_os/kairos_state.json").expanduser()
TICK_SECONDS = 60          # how often KAIROS checks
DREAM_EVERY  = 10          # ticks between autoDream
ALERT_FILE   = Path("~/.luo_os/kairos_alerts.json").expanduser()

GR="[92m"; RD="[91m"; YL="[93m"; CY="[96m"
B="[1m"; R="[0m"; DIM="[2m"

# ── Watch rules — what KAIROS monitors proactively ────────────────────
WATCH_RULES = [
    {
        "name":    "high_memory",
        "check":   "memory",
        "threshold": 85,        # % RAM used
        "action":  "alert",
        "message": "RAM usage above {value}% — consider closing apps or freeing memory",
    },
    {
        "name":    "high_disk",
        "check":   "disk",
        "threshold": 90,
        "action":  "alert",
        "message": "Disk usage above {value}% — clean up or expand storage",
    },
    {
        "name":    "luokai_ready",
        "check":   "service",
        "service": "luokai",
        "action":  "alert",
        "message": "LUOKAI neural engine is running",
    },
    {
        "name":    "agent_api_down",
        "check":   "service",
        "service": "agent_api",
        "action":  "alert",
        "message": "Agent API (port 7070) is offline",
    },
    {
        "name":    "large_log_files",
        "check":   "file_size",
        "path":    "~/.luo_os",
        "threshold": 100,       # MB
        "action":  "suggest",
        "message": "Log files are large ({value}MB) — run: kairos clean",
    },
]


class KairosState:
    """Persistent KAIROS state across restarts."""

    def __init__(self):
        KAIROS_STATE.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(KAIROS_STATE.read_text()) if KAIROS_STATE.exists() else {}
        except Exception:
            return {}

    def save(self):
        KAIROS_STATE.write_text(json.dumps(self.data, indent=2))

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def increment(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        self.save()
        return self.data[key]


class KairosAlert:
    """Alert system — stores and displays proactive alerts."""

    def __init__(self):
        ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list:
        try:
            return json.loads(ALERT_FILE.read_text()) if ALERT_FILE.exists() else []
        except Exception:
            return []

    def add(self, name: str, message: str, level: str = "info"):
        alerts = self._load()
        # deduplicate — don't spam same alert
        existing = [a for a in alerts if a["name"] == name]
        if existing:
            last = existing[-1]
            last_time = datetime.fromisoformat(last["time"])
            if datetime.now() - last_time < timedelta(hours=1):
                return  # already alerted recently
        alerts.append({
            "name":    name,
            "message": message,
            "level":   level,
            "time":    datetime.now().isoformat(),
            "read":    False,
        })
        # keep last 50
        alerts = alerts[-50:]
        ALERT_FILE.write_text(json.dumps(alerts, indent=2))

    def get_unread(self) -> list:
        alerts = self._load()
        return [a for a in alerts if not a["read"]]

    def mark_read(self):
        alerts = self._load()
        for a in alerts:
            a["read"] = True
        ALERT_FILE.write_text(json.dumps(alerts, indent=2))

    def print_unread(self):
        unread = self.get_unread()
        if not unread:
            return
        print(f"\n{YL}{B}⚠ KAIROS Alerts ({len(unread)}){R}")
        for a in unread:
            level_color = RD if a["level"]=="critical" else YL if a["level"]=="warn" else CY
            ts = a["time"][:16]
            print(f"  {level_color}[{a['level'].upper()}]{R} {a['message']} {DIM}({ts}){R}")
        self.mark_read()


class KAIROS:
    """
    KAIROS — Always-on proactive background agent.

    Runs a tick loop. Each tick it:
    1. Checks system health (RAM, disk, services)
    2. Watches file changes in the project
    3. Processes background task queue
    4. Runs autoDream memory consolidation periodically
    5. Asks the LLM if there's anything proactive to do
    6. Logs everything to ~/.luo_os/kairos.log
    """

    def __init__(self, config: LuoConfig = None):
        self.config  = config or LuoConfig()
        self.llm     = None  # LUOKAI native — no external LLM needed
        self.memory  = MemorySystem(
            self.config.memory_file,
            self.config.notes_dir,
            self.config.sessions_dir
        )
        self.state   = KairosState()
        self.alerts  = KairosAlert()
        self.running = False
        self.tick    = 0
        self._file_hashes = {}
        KAIROS_LOG.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, msg: str, level: str = "info"):
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = RD if level=="error" else YL if level=="warn" else CY if level=="kairos" else DIM
        entry = f"[{ts}] [{level.upper()}] {msg}\n"
        print(f"{color}{entry.strip()}{R}")
        try:
            with open(KAIROS_LOG, "a") as f:
                f.write(entry)
        except Exception:
            pass

    # ── System checks ─────────────────────────────────────────────────

    def _check_memory(self) -> dict:
        try:
            result = subprocess.run(
                "free -m | awk 'NR==2{print int($3/$2*100)}'",
                shell=True, capture_output=True, text=True
            )
            pct = int(result.stdout.strip() or 0)
            return {"ok": pct < 85, "value": pct, "unit": "%"}
        except Exception:
            return {"ok": True, "value": 0, "unit": "%"}

    def _check_disk(self) -> dict:
        try:
            result = subprocess.run(
                "df / | awk 'NR==2{print int($3/$2*100)}'",
                shell=True, capture_output=True, text=True
            )
            pct = int(result.stdout.strip() or 0)
            return {"ok": pct < 90, "value": pct, "unit": "%"}
        except Exception:
            return {"ok": True, "value": 0, "unit": "%"}

    def _check_service(self, name: str) -> bool:
        ports = {"luokai": 3000, "agent_api": 7070, "rest_api": 8080}
        port  = ports.get(name)
        if not port:
            return True
        try:
            import socket
            s = socket.socket()
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except Exception:
            return False

    def _check_log_size(self) -> dict:
        try:
            log_dir = Path("~/.luo_os").expanduser()
            total   = sum(f.stat().st_size for f in log_dir.rglob("*.log") if f.is_file())
            mb      = total / 1_000_000
            return {"ok": mb < 100, "value": round(mb, 1), "unit": "MB"}
        except Exception:
            return {"ok": True, "value": 0, "unit": "MB"}

    def _run_watch_rules(self):
        """Run all watch rules and fire alerts if needed."""
        for rule in WATCH_RULES:
            try:
                check = rule["check"]

                if check == "memory":
                    result = self._check_memory()
                    if not result["ok"]:
                        msg = rule["message"].format(value=result["value"])
                        self.alerts.add(rule["name"], msg, "warn")
                        self._log(f"Alert: {msg}", "warn")

                elif check == "disk":
                    result = self._check_disk()
                    if not result["ok"]:
                        msg = rule["message"].format(value=result["value"])
                        self.alerts.add(rule["name"], msg, "warn")
                        self._log(f"Alert: {msg}", "warn")

                elif check == "service":
                    up = self._check_service(rule["service"])
                    if not up:
                        self.alerts.add(rule["name"], rule["message"], "warn")
                        self._log(f"Alert: {rule['message']}", "warn")

                elif check == "file_size":
                    result = self._check_log_size()
                    if not result["ok"]:
                        msg = rule["message"].format(value=result["value"])
                        self.alerts.add(rule["name"], msg, "info")

            except Exception as e:
                self._log(f"Watch rule {rule['name']} error: {e}", "error")

    # ── File watcher ──────────────────────────────────────────────────

    def _hash_file(self, path: Path) -> str:
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _watch_files(self, watch_paths: list = None):
        """Watch key files for changes, log what changed."""
        paths = watch_paths or [
            Path("luo_agent"),
            Path("ai_core"),
            Path("shell"),
        ]
        changed = []
        for base in paths:
            if not base.exists():
                continue
            for f in base.rglob("*.py"):
                h = self._hash_file(f)
                old = self._file_hashes.get(str(f))
                if old and old != h:
                    changed.append(str(f))
                self._file_hashes[str(f)] = h

        if changed:
            self._log(f"Files changed: {', '.join(changed[:5])}", "kairos")
            self.memory.append_memory(f"KAIROS: files changed — {', '.join(changed[:3])}")

    # ── Proactive LLM tick ────────────────────────────────────────────

    def _proactive_think(self):
        """
        Ask the LLM if there's anything proactive to do
        based on current system state and memory.
        Runs via LUOKAI native inference.
        """
        if not self.llm.is_available():
            return

        mem_summary = self.memory.get_context_summary()
        mem_size    = self._check_memory()
        disk_size   = self._check_disk()

        prompt = f"""You are KAIROS, the always-on proactive AI agent in Luo OS.
Current system state:
- RAM usage: {mem_size["value"]}%
- Disk usage: {disk_size["value"]}%
- Tick: #{self.tick}
- Time: {datetime.now().strftime("%H:%M %Y-%m-%d")}

Recent memory:
{mem_summary[:500]}

Based on this, is there anything useful you should proactively do or suggest?
If nothing useful, respond with exactly: NOTHING
If there is something, respond with a single short action or suggestion (1-2 sentences max).
Do NOT be verbose. Only respond if genuinely useful."""

        try:
            response = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.4, max_tokens=100
            )
            if response and "NOTHING" not in response and not response.startswith("[ERROR]"):
                self._log(f"Proactive: {response}", "kairos")
                self.alerts.add("kairos_proactive", response, "info")
                self.memory.append_memory(f"KAIROS proactive: {response[:100]}")
        except Exception as e:
            self._log(f"Proactive think error: {e}", "error")

    # ── Background task queue ─────────────────────────────────────────

    def _process_task_queue(self):
        """Process any tasks queued for KAIROS."""
        queue_file = Path("~/.luo_os/kairos_tasks.json").expanduser()
        if not queue_file.exists():
            return
        try:
            tasks   = json.loads(queue_file.read_text())
            pending = [t for t in tasks if t.get("status") == "pending"]
            if not pending:
                return
            task = pending[0]
            self._log(f"Processing task: {task['task'][:60]}", "kairos")
            if self.llm.is_available():
                result = self.llm.chat(
                    [{"role": "user", "content": task["task"]}],
                    temperature=0.7, max_tokens=512
                )
                task["status"]    = "done"
                task["result"]    = result[:400]
                task["completed"] = datetime.now().isoformat()
                self._log(f"Task done: {result[:80]}", "kairos")
            updated = [t if t.get("id") != task.get("id") else task for t in tasks]
            queue_file.write_text(json.dumps(updated, indent=2))
        except Exception as e:
            self._log(f"Task queue error: {e}", "error")

    def queue_task(self, task: str, priority: int = 5):
        """Queue a task for KAIROS to process in background."""
        queue_file = Path("~/.luo_os/kairos_tasks.json").expanduser()
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        tasks = []
        if queue_file.exists():
            try:
                tasks = json.loads(queue_file.read_text())
            except Exception:
                pass
        import uuid
        tasks.append({
            "id":       str(uuid.uuid4())[:8],
            "task":     task,
            "priority": priority,
            "status":   "pending",
            "queued":   datetime.now().isoformat(),
        })
        tasks.sort(key=lambda t: t["priority"], reverse=True)
        queue_file.write_text(json.dumps(tasks, indent=2))
        self._log(f"Task queued: {task[:60]}", "kairos")

    # ── Clean up ──────────────────────────────────────────────────────

    def clean_logs(self):
        """Delete old log files to free space."""
        log_dir = Path("~/.luo_os").expanduser()
        deleted = 0
        for f in log_dir.rglob("*.log"):
            if f.stat().st_size > 10_000_000:  # > 10MB
                f.unlink()
                deleted += 1
        self._log(f"Cleaned {deleted} large log files", "kairos")
        return deleted

    # ── Main tick loop ────────────────────────────────────────────────

    def _tick(self):
        self.tick += 1
        self.state.increment("total_ticks")
        self._log(f"Tick #{self.tick}", "kairos")

        # always run
        self._run_watch_rules()
        self._process_task_queue()
        self._watch_files()

        # every 5 ticks: proactive LLM think
        if self.tick % 5 == 0:
            threading.Thread(target=self._proactive_think, daemon=True).start()

        # every 10 ticks: autoDream memory consolidation
        if self.tick % DREAM_EVERY == 0:
            self._log("Running autoDream...", "kairos")
            if self.llm.is_available():
                result = self.memory.auto_dream(self.llm)
                self._log(f"autoDream: {result}", "kairos")

        # save state
        self.state.set("last_tick", datetime.now().isoformat())
        self.state.set("tick_count", self.tick)

    def start(self):
        """Start KAIROS daemon loop."""
        self._log(f"KAIROS starting — tick every {TICK_SECONDS}s", "kairos")
        self._log("LUOKAI native inference engine", "kairos")
        self.running = True
        # initial file hash scan
        self._watch_files()
        while self.running:
            try:
                self._tick()
            except Exception as e:
                self._log(f"Tick error: {e}", "error")
            time.sleep(TICK_SECONDS)

    def stop(self):
        self.running = False
        self._log("KAIROS stopped", "kairos")

    def status(self) -> dict:
        return {
            "running":    self.running,
            "tick":       self.tick,
            "total_ticks": self.state.get("total_ticks", 0),
            "last_tick":  self.state.get("last_tick", "never"),
            "model":      self.config.model,
            "luokai":     True,
            "unread_alerts": len(self.alerts.get_unread()),
            "memory_file": str(self.config.memory_file),
        }

    def print_status(self):
        """Print KAIROS status."""
        s = self.status()
        print("KAIROS | running=" + str(s.get("running")) + " | alerts=" + str(s.get("unread_alerts", 0)) + " unread")

#!/usr/bin/env python3
"""
Luo OS — KAIROS Mode
=====================
Always-on proactive agent. Runs in background, acts without being asked.
Watches files, monitors system, queues tasks, sends alerts.

Inspired by Claude Code leak architecture concept — clean-room implementation.
Author: Abd El-Rahman Abbas (Mr. Kai) — Luo OS
"""

import os, sys, json, time, threading, subprocess, hashlib
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "luo_agent"))

from core.config import LuoConfig

from memory.memory import MemorySystem

# ── Config ────────────────────────────────────────────────────────────
KAIROS_LOG   = Path("~/.luo_os/kairos.log").expanduser()
KAIROS_STATE = Path("~/.luo_os/kairos_state.json").expanduser()
TICK_SECONDS = 60          # how often KAIROS checks
DREAM_EVERY  = 10          # ticks between autoDream
ALERT_FILE   = Path("~/.luo_os/kairos_alerts.json").expanduser()

GR="[92m"; RD="[91m"; YL="[93m"; CY="[96m"
B="[1m"; R="[0m"; DIM="[2m"

# ── Watch rules — what KAIROS monitors proactively ────────────────────
WATCH_RULES = [
    {
        "name":    "high_memory",
        "check":   "memory",
        "threshold": 85,        # % RAM used
        "action":  "alert",
        "message": "RAM usage above {value}% — consider closing apps or freeing memory",
    },
    {
        "name":    "high_disk",
        "check":   "disk",
        "threshold": 90,
        "action":  "alert",
        "message": "Disk usage above {value}% — clean up or expand storage",
    },
    {
        "name":    "luokai_ready",
        "check":   "service",
        "service": "luokai",
        "action":  "alert",
        "message": "LUOKAI neural engine is running",
    },
    {
        "name":    "agent_api_down",
        "check":   "service",
        "service": "agent_api",
        "action":  "alert",
        "message": "Agent API (port 7070) is offline",
    },
    {
        "name":    "large_log_files",
        "check":   "file_size",
        "path":    "~/.luo_os",
        "threshold": 100,       # MB
        "action":  "suggest",
        "message": "Log files are large ({value}MB) — run: kairos clean",
    },
]


class KairosState:
    """Persistent KAIROS state across restarts."""

    def __init__(self):
        KAIROS_STATE.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(KAIROS_STATE.read_text()) if KAIROS_STATE.exists() else {}
        except Exception:
            return {}

    def save(self):
        KAIROS_STATE.write_text(json.dumps(self.data, indent=2))

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def increment(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        self.save()
        return self.data[key]


class KairosAlert:
    """Alert system — stores and displays proactive alerts."""

    def __init__(self):
        ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list:
        try:
            return json.loads(ALERT_FILE.read_text()) if ALERT_FILE.exists() else []
        except Exception:
            return []

    def add(self, name: str, message: str, level: str = "info"):
        alerts = self._load()
        # deduplicate — don't spam same alert
        existing = [a for a in alerts if a["name"] == name]
        if existing:
            last = existing[-1]
            last_time = datetime.fromisoformat(last["time"])
            if datetime.now() - last_time < timedelta(hours=1):
                return  # already alerted recently
        alerts.append({
            "name":    name,
            "message": message,
            "level":   level,
            "time":    datetime.now().isoformat(),
            "read":    False,
        })
        # keep last 50
        alerts = alerts[-50:]
        ALERT_FILE.write_text(json.dumps(alerts, indent=2))

    def get_unread(self) -> list:
        alerts = self._load()
        return [a for a in alerts if not a["read"]]

    def mark_read(self):
        alerts = self._load()
        for a in alerts:
            a["read"] = True
        ALERT_FILE.write_text(json.dumps(alerts, indent=2))

    def print_unread(self):
        unread = self.get_unread()
        if not unread:
            return
        print(f"\n{YL}{B}⚠ KAIROS Alerts ({len(unread)}){R}")
        for a in unread:
            level_color = RD if a["level"]=="critical" else YL if a["level"]=="warn" else CY
            ts = a["time"][:16]
            print(f"  {level_color}[{a['level'].upper()}]{R} {a['message']} {DIM}({ts}){R}")
        self.mark_read()


class KAIROS:
    """
    KAIROS — Always-on proactive background agent.

    Runs a tick loop. Each tick it:
    1. Checks system health (RAM, disk, services)
    2. Watches file changes in the project
    3. Processes background task queue
    4. Runs autoDream memory consolidation periodically
    5. Asks the LLM if there's anything proactive to do
    6. Logs everything to ~/.luo_os/kairos.log
    """

    def __init__(self, config: LuoConfig = None):
        self.config  = config or LuoConfig()
        self.llm     = None  # LUOKAI native — no external LLM needed
        self.memory  = MemorySystem(
            self.config.memory_file,
            self.config.notes_dir,
            self.config.sessions_dir
        )
        self.state   = KairosState()
        self.alerts  = KairosAlert()
        self.running = False
        self.tick    = 0
        self._file_hashes = {}
        KAIROS_LOG.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, msg: str, level: str = "info"):
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = RD if level=="error" else YL if level=="warn" else CY if level=="kairos" else DIM
        entry = f"[{ts}] [{level.upper()}] {msg}\n"
        print(f"{color}{entry.strip()}{R}")
        try:
            with open(KAIROS_LOG, "a") as f:
                f.write(entry)
        except Exception:
            pass

    # ── System checks ─────────────────────────────────────────────────

    def _check_memory(self) -> dict:
        try:
            result = subprocess.run(
                "free -m | awk 'NR==2{print int($3/$2*100)}'",
                shell=True, capture_output=True, text=True
            )
            pct = int(result.stdout.strip() or 0)
            return {"ok": pct < 85, "value": pct, "unit": "%"}
        except Exception:
            return {"ok": True, "value": 0, "unit": "%"}

    def _check_disk(self) -> dict:
        try:
            result = subprocess.run(
                "df / | awk 'NR==2{print int($3/$2*100)}'",
                shell=True, capture_output=True, text=True
            )
            pct = int(result.stdout.strip() or 0)
            return {"ok": pct < 90, "value": pct, "unit": "%"}
        except Exception:
            return {"ok": True, "value": 0, "unit": "%"}

    def _check_service(self, name: str) -> bool:
        ports = {"luokai": 3000, "agent_api": 7070, "rest_api": 8080}
        port  = ports.get(name)
        if not port:
            return True
        try:
            import socket
            s = socket.socket()
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except Exception:
            return False

    def _check_log_size(self) -> dict:
        try:
            log_dir = Path("~/.luo_os").expanduser()
            total   = sum(f.stat().st_size for f in log_dir.rglob("*.log") if f.is_file())
            mb      = total / 1_000_000
            return {"ok": mb < 100, "value": round(mb, 1), "unit": "MB"}
        except Exception:
            return {"ok": True, "value": 0, "unit": "MB"}

    def _run_watch_rules(self):
        """Run all watch rules and fire alerts if needed."""
        for rule in WATCH_RULES:
            try:
                check = rule["check"]

                if check == "memory":
                    result = self._check_memory()
                    if not result["ok"]:
                        msg = rule["message"].format(value=result["value"])
                        self.alerts.add(rule["name"], msg, "warn")
                        self._log(f"Alert: {msg}", "warn")

                elif check == "disk":
                    result = self._check_disk()
                    if not result["ok"]:
                        msg = rule["message"].format(value=result["value"])
                        self.alerts.add(rule["name"], msg, "warn")
                        self._log(f"Alert: {msg}", "warn")

                elif check == "service":
                    up = self._check_service(rule["service"])
                    if not up:
                        self.alerts.add(rule["name"], rule["message"], "warn")
                        self._log(f"Alert: {rule['message']}", "warn")

                elif check == "file_size":
                    result = self._check_log_size()
                    if not result["ok"]:
                        msg = rule["message"].format(value=result["value"])
                        self.alerts.add(rule["name"], msg, "info")

            except Exception as e:
                self._log(f"Watch rule {rule['name']} error: {e}", "error")

    # ── File watcher ──────────────────────────────────────────────────

    def _hash_file(self, path: Path) -> str:
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _watch_files(self, watch_paths: list = None):
        """Watch key files for changes, log what changed."""
        paths = watch_paths or [
            Path("luo_agent"),
            Path("ai_core"),
            Path("shell"),
        ]
        changed = []
        for base in paths:
            if not base.exists():
                continue
            for f in base.rglob("*.py"):
                h = self._hash_file(f)
                old = self._file_hashes.get(str(f))
                if old and old != h:
                    changed.append(str(f))
                self._file_hashes[str(f)] = h

        if changed:
            self._log(f"Files changed: {', '.join(changed[:5])}", "kairos")
            self.memory.append_memory(f"KAIROS: files changed — {', '.join(changed[:3])}")

    # ── Proactive LLM tick ────────────────────────────────────────────

    def _proactive_think(self):
        """
        Ask the LLM if there's anything proactive to do
        based on current system state and memory.
        Runs via LUOKAI native inference.
        """
        if not self.llm.is_available():
            return

        mem_summary = self.memory.get_context_summary()
        mem_size    = self._check_memory()
        disk_size   = self._check_disk()

        prompt = f"""You are KAIROS, the always-on proactive AI agent in Luo OS.
Current system state:
- RAM usage: {mem_size["value"]}%
- Disk usage: {disk_size["value"]}%
- Tick: #{self.tick}
- Time: {datetime.now().strftime("%H:%M %Y-%m-%d")}

Recent memory:
{mem_summary[:500]}

Based on this, is there anything useful you should proactively do or suggest?
If nothing useful, respond with exactly: NOTHING
If there is something, respond with a single short action or suggestion (1-2 sentences max).
Do NOT be verbose. Only respond if genuinely useful."""

        try:
            response = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.4, max_tokens=100
            )
            if response and "NOTHING" not in response and not response.startswith("[ERROR]"):
                self._log(f"Proactive: {response}", "kairos")
                self.alerts.add("kairos_proactive", response, "info")
                self.memory.append_memory(f"KAIROS proactive: {response[:100]}")
        except Exception as e:
            self._log(f"Proactive think error: {e}", "error")

    # ── Background task queue ─────────────────────────────────────────

    def _process_task_queue(self):
        """Process any tasks queued for KAIROS."""
        queue_file = Path("~/.luo_os/kairos_tasks.json").expanduser()
        if not queue_file.exists():
            return
        try:
            tasks   = json.loads(queue_file.read_text())
            pending = [t for t in tasks if t.get("status") == "pending"]
            if not pending:
                return
            task = pending[0]
            self._log(f"Processing task: {task['task'][:60]}", "kairos")
            if self.llm.is_available():
                result = self.llm.chat(
                    [{"role": "user", "content": task["task"]}],
                    temperature=0.7, max_tokens=512
                )
                task["status"]    = "done"
                task["result"]    = result[:400]
                task["completed"] = datetime.now().isoformat()
                self._log(f"Task done: {result[:80]}", "kairos")
            updated = [t if t.get("id") != task.get("id") else task for t in tasks]
            queue_file.write_text(json.dumps(updated, indent=2))
        except Exception as e:
            self._log(f"Task queue error: {e}", "error")

    def queue_task(self, task: str, priority: int = 5):
        """Queue a task for KAIROS to process in background."""
        queue_file = Path("~/.luo_os/kairos_tasks.json").expanduser()
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        tasks = []
        if queue_file.exists():
            try:
                tasks = json.loads(queue_file.read_text())
            except Exception:
                pass
        import uuid
        tasks.append({
            "id":       str(uuid.uuid4())[:8],
            "task":     task,
            "priority": priority,
            "status":   "pending",
            "queued":   datetime.now().isoformat(),
        })
        tasks.sort(key=lambda t: t["priority"], reverse=True)
        queue_file.write_text(json.dumps(tasks, indent=2))
        self._log(f"Task queued: {task[:60]}", "kairos")

    # ── Clean up ──────────────────────────────────────────────────────

    def clean_logs(self):
        """Delete old log files to free space."""
        log_dir = Path("~/.luo_os").expanduser()
        deleted = 0
        for f in log_dir.rglob("*.log"):
            if f.stat().st_size > 10_000_000:  # > 10MB
                f.unlink()
                deleted += 1
        self._log(f"Cleaned {deleted} large log files", "kairos")
        return deleted

    # ── Main tick loop ────────────────────────────────────────────────

    def _tick(self):
        self.tick += 1
        self.state.increment("total_ticks")
        self._log(f"Tick #{self.tick}", "kairos")

        # always run
        self._run_watch_rules()
        self._process_task_queue()
        self._watch_files()

        # every 5 ticks: proactive LLM think
        if self.tick % 5 == 0:
            threading.Thread(target=self._proactive_think, daemon=True).start()

        # every 10 ticks: autoDream memory consolidation
        if self.tick % DREAM_EVERY == 0:
            self._log("Running autoDream...", "kairos")
            if self.llm.is_available():
                result = self.memory.auto_dream(self.llm)
                self._log(f"autoDream: {result}", "kairos")

        # save state
        self.state.set("last_tick", datetime.now().isoformat())
        self.state.set("tick_count", self.tick)

    def start(self):
        """Start KAIROS daemon loop."""
        self._log(f"KAIROS starting — tick every {TICK_SECONDS}s", "kairos")
        self._log("LUOKAI native inference engine", "kairos")
        self.running = True
        # initial file hash scan
        self._watch_files()
        while self.running:
            try:
                self._tick()
            except Exception as e:
                self._log(f"Tick error: {e}", "error")
            time.sleep(TICK_SECONDS)

    def stop(self):
        self.running = False
        self._log("KAIROS stopped", "kairos")

    def status(self) -> dict:
        return {
            "running":    self.running,
            "tick":       self.tick,
            "total_ticks": self.state.get("total_ticks", 0),
            "last_tick":  self.state.get("last_tick", "never"),
            "model":      self.config.model,
            "luokai":     True,
            "unread_alerts": len(self.alerts.get_unread()),
            "memory_file": str(self.config.memory_file),
        }

    def print_status(self):
        s = self.status()
        print(f"{CY}{B}── KAIROS Status ──────────────────────{R}")
        print(f"  Running   : {GR}yes{R}" if s["running"] else f"  Running   : {RD}no{R}")
        print(f"  Tick      : #{s['tick']}")
        print(f"  Last tick : {s['last_tick'][:19] if s['last_tick'] != 'never' else 'never'}")
        print(f"  Model     : {s['model']}")
        print(f"  LUOKAI    : {GR}online{R}")
        print(str(s.get("unread_alerts",0)) + " unread alerts")
        print("-" * 40)



# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, signal
    config  = LuoConfig()
    kairos  = KAIROS(config)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            kairos.print_status()
            kairos.alerts.print_unread()
        elif cmd == "alerts":
            kairos.alerts.print_unread()
        elif cmd == "clean":
            n = kairos.clean_logs()
            print(f"Cleaned {n} log files")
        elif cmd == "task" and len(sys.argv) > 2:
            task = " ".join(sys.argv[2:])
            kairos.queue_task(task)
            print(f"Task queued: {task}")
        elif cmd == "start":
            def _stop(sig, frame):
                kairos.stop(); sys.exit(0)
            signal.signal(signal.SIGINT,  _stop)
            signal.signal(signal.SIGTERM, _stop)
            kairos.start()
    else:
        # default: start
        def _stop(sig, frame):
            kairos.stop(); sys.exit(0)
        signal.signal(signal.SIGINT,  _stop)
        signal.signal(signal.SIGTERM, _stop)
        kairos.start()
