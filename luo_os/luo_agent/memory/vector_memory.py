#!/usr/bin/env python3
"""
Luo OS — Vector Memory (powered by ChromaDB)
Upgrades flat MEMORY.md to semantic vector search.
Agents find relevant memories by meaning, not just text matching.
"""
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class VectorMemory:
    """
    Semantic memory system using ChromaDB.
    Falls back to flat MEMORY.md if ChromaDB unavailable.
    """
    def __init__(self, agent_id: str, persist_dir: str = "~/.luo_os/chroma"):
        self.agent_id  = agent_id
        self.persist   = Path(persist_dir).expanduser()
        self.persist.mkdir(parents=True, exist_ok=True)
        self.available = CHROMA_AVAILABLE
        self._client   = None
        self._col      = None
        if self.available:
            try:
                self._client = chromadb.PersistentClient(path=str(self.persist))
                self._col    = self._client.get_or_create_collection(
                    name=f"agent_{agent_id[:20]}",
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"[VectorMemory] ChromaDB ready — {self._col.count()} memories")
            except Exception as e:
                print(f"[VectorMemory] ChromaDB init failed: {e} — using flat memory")
                self.available = False

    def add(self, text: str, metadata: dict = None) -> str:
        """Add a memory. Returns memory ID."""
        ts  = datetime.now().isoformat()
        mid = f"mem_{ts.replace(':','-').replace('.','-')}"
        meta = {"timestamp": ts, "agent": self.agent_id}
        if metadata:
            meta.update(metadata)
        if self.available and self._col:
            try:
                self._col.add(documents=[text], ids=[mid], metadatas=[meta])
                return mid
            except Exception as e:
                print(f"[VectorMemory] add error: {e}")
        return mid

    def search(self, query: str, n: int = 5) -> list:
        """Semantic search — find memories by meaning."""
        if self.available and self._col:
            try:
                results = self._col.query(query_texts=[query], n_results=min(n, max(1, self._col.count())))
                docs  = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]
                return [{"text": d, "meta": m, "score": 1-s}
                        for d, m, s in zip(docs, metas, dists)]
            except Exception as e:
                print(f"[VectorMemory] search error: {e}")
        return []

    def get_all(self) -> list:
        """Get all memories."""
        if self.available and self._col:
            try:
                r = self._col.get()
                return [{"text": d, "meta": m}
                        for d, m in zip(r["documents"], r["metadatas"])]
            except Exception:
                pass
        return []

    def delete(self, memory_id: str) -> bool:
        if self.available and self._col:
            try:
                self._col.delete(ids=[memory_id]); return True
            except Exception:
                pass
        return False

    def count(self) -> int:
        if self.available and self._col:
            try: return self._col.count()
            except Exception: pass
        return 0

    def get_context(self, query: str, n: int = 5) -> str:
        """Get relevant memory context for a query — inject into agent prompts."""
        results = self.search(query, n=n)
        if not results:
            return ""
        lines = [f"- {r['text']}" for r in results]
        return "## Relevant memories (semantic search):\n" + "\n".join(lines)

    def clear(self):
        if self.available and self._col:
            try:
                self._client.delete_collection(f"agent_{self.agent_id[:20]}")
                self._col = self._client.get_or_create_collection(f"agent_{self.agent_id[:20]}")
            except Exception:
                pass
