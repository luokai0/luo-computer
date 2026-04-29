import time, json, signal, sys
from pathlib import Path
from datetime import datetime
from core.config import LuoConfig
from core.llm import OllamaClient  # LUOKAI compat shim
from memory.memory import MemorySystem
from agents.agent import LuoAgentCore

LOG   = Path("~/.luo_agent/daemon.log").expanduser()
QUEUE = Path("~/.luo_agent/tasks.json").expanduser()

class LuoDaemon:
    def __init__(self, config):
        self.config=config; self.running=False; self.tick=0
        self.memory=MemorySystem(config.memory_file,config.notes_dir,config.sessions_dir)
        self.llm=OllamaClient()
        self.agent=LuoAgentCore(config,self.memory)
        signal.signal(signal.SIGINT,self._stop)
        signal.signal(signal.SIGTERM,self._stop)

    def _stop(self,*_): self._log("Stopping..."); self.running=False; sys.exit(0)

    def _log(self, msg):
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"); e=f"[{ts}] {msg}\n"
        print(e,end="")
        try: LOG.parent.mkdir(parents=True,exist_ok=True); open(LOG,"a").write(e)
        except: pass

    def _tasks(self):
        try: return json.loads(QUEUE.read_text()) if QUEUE.exists() else []
        except: return []

    def _save(self,t):
        QUEUE.parent.mkdir(parents=True,exist_ok=True)
        QUEUE.write_text(json.dumps(t,indent=2))

    def queue_task(self, task, priority=5):
        tasks=self._tasks()
        tasks.append({"task":task,"priority":priority,"queued":datetime.now().isoformat(),"status":"pending"})
        tasks.sort(key=lambda x:x["priority"],reverse=True)
        self._save(tasks); self._log(f"Queued: {task[:60]}")

    def _process(self):
        tasks=self._tasks(); pending=[t for t in tasks if t["status"]=="pending"]
        if not pending: return
        t=pending[0]; self._log(f"Processing: {t['task'][:60]}")
        try:
            t["result"]=self.agent.chat(t["task"])[:400]
            t["status"]="done"; t["completed"]=datetime.now().isoformat()
        except Exception as e: t["status"]="error"; t["error"]=str(e)
        self._save([x if x.get("queued")!=t.get("queued") else t for x in tasks])

    def start(self):
        self._log(f"Luo Daemon started — model:{self.config.model}")
        self.running=True
        while self.running:
            self.tick+=1; self._log(f"Tick #{self.tick}")
            self._process()
            if self.tick%10==0 and self.llm.is_available():
                self._log(self.memory.auto_dream(self.llm))
            time.sleep(self.config.get("daemon_tick_seconds",30))
