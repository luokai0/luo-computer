import json, hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

HDR = "# Luo Agent Memory\n<!-- Auto-managed -->\n\n"

class MemorySystem:
    def __init__(self, memory_file, notes_dir, sessions_dir):
        self.memory_file=memory_file; self.notes_dir=notes_dir; self.sessions_dir=sessions_dir
        if not memory_file.exists(): memory_file.write_text(HDR)

    def read_memory(self):
        try: return self.memory_file.read_text()
        except: return ""

    def append_memory(self, fact):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(self.memory_file,"a") as f: f.write(f"- [{ts}] {fact.strip()}\n")

    def save_note(self, title, content):
        nid = hashlib.md5(title.encode()).hexdigest()[:8]
        fn  = self.notes_dir / f"{nid}_{title[:30].replace(' ','_')}.md"
        fn.write_text(f"# {title}\n_{datetime.now().isoformat()}_\n\n{content}\n")
        self.append_memory(f"Note: {title}"); return nid

    def load_note(self, q):
        for f in self.notes_dir.glob("*.md"):
            if q in f.name: return f.read_text()
        return None

    def list_notes(self): return [f.name for f in sorted(self.notes_dir.glob("*.md"))]

    def save_session(self, sid, messages):
        with open(self.sessions_dir/f"{sid}.json","w") as f:
            json.dump({"id":sid,"messages":messages,"saved":datetime.now().isoformat()},f,indent=2)

    def load_session(self, sid):
        p = self.sessions_dir/f"{sid}.json"
        return json.loads(p.read_text()).get("messages",[]) if p.exists() else []

    def list_sessions(self):
        return [f.stem for f in sorted(self.sessions_dir.glob("*.json"),reverse=True)]

    def auto_dream(self, llm):
        mem = self.read_memory()
        if len(mem.strip()) < 100: return "Nothing to consolidate."
        result = llm.chat([{"role":"user","content":
            f"Consolidate this memory into max 20 clean bullet points. Return ONLY the bullet list:\n{mem}"}],
            temperature=0.3, max_tokens=1024)
        if result and not result.startswith("[ERROR]"):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.memory_file.write_text(f"{HDR}<!-- Consolidated: {ts} -->\n\n{result}\n")
            return f"Consolidated at {ts}"
        return "Skipped (model unavailable)"

    def get_context_summary(self):
        mem = self.read_memory(); recent = self.list_sessions()[:3]
        s = f"## Memory\n{mem}\n"
        if recent: s += "\n## Recent Sessions\n" + "\n".join(f"- {x}" for x in recent)
        return s
