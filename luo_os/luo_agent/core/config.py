import json
from pathlib import Path

DEFAULT = {
    "model": "luokai", "luokai_url": "http://localhost:3000",
    "memory_file": "~/.luo_agent/MEMORY.md", "notes_dir": "~/.luo_agent/notes/",
    "sessions_dir": "~/.luo_agent/sessions/", "daemon_tick_seconds": 30,
    "max_tokens": 2048, "temperature": 0.7, "auto_dream": True, "version": "0.1.0"
}

class LuoConfig:
    def __init__(self, config_path="~/.luo_agent/config.json"):
        self.config_path = Path(config_path).expanduser()
        self.data = DEFAULT.copy()
        self._load(); self._ensure_dirs()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path) as f: self.data.update(json.load(f))
            except Exception: pass

    def _ensure_dirs(self):
        for key in ["memory_file","notes_dir","sessions_dir"]:
            p = Path(self.data[key]).expanduser()
            (p.parent if key=="memory_file" else p).mkdir(parents=True, exist_ok=True)

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path,"w") as f: json.dump(self.data,f,indent=2)

    def get(self, k, d=None): return self.data.get(k,d)
    def set(self, k, v): self.data[k]=v; self.save()

    @property
    def model(self): return self.data["model"]
    @property
    def ollama_url(self): return self.data.get("luokai_url", "http://localhost:3000")
    @property
    def memory_file(self): return Path(self.data["memory_file"]).expanduser()
    @property
    def notes_dir(self): return Path(self.data["notes_dir"]).expanduser()
    @property
    def sessions_dir(self): return Path(self.data["sessions_dir"]).expanduser()
