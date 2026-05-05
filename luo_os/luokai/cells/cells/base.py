#!/usr/bin/env python3
"""
luokai/cells/base.py — LUOKAI Cell Architecture
=================================================
Python port of the cell system from cells_and_data.rar.
Every cell has: id, category, name, state, connections, specializedData.
Cells learn from data and process inputs independently.
"""
import json, time, hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional

class BaseCell:
    """Base cell — all LUOKAI cells inherit this."""
    category: str = "base"

    def __init__(self, name: str):
        self.id = hashlib.md5(f"{self.category}:{name}:{time.time()}".encode()).hexdigest()[:12]
        self.name = name
        self.state = 0
        self.connections: List[str] = []         # cell IDs this connects to
        self.specialized_data: List[Any] = []    # learned knowledge
        self._created = time.time()
        self._activations = 0

    def process(self, signal: Any) -> Any:
        """Process a signal — override in subclasses."""
        self.state += 1
        self._activations += 1
        return signal

    def learn(self, data: Any) -> None:
        """Store learned data in this cell."""
        self.specialized_data.append(data)
        # Keep bounded — cap at 10,000 entries per cell
        if len(self.specialized_data) > 10_000:
            self.specialized_data = self.specialized_data[-8_000:]

    def connect(self, other_cell_id: str) -> None:
        if other_cell_id not in self.connections:
            self.connections.append(other_cell_id)

    def status(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "state": self.state,
            "activations": self._activations,
            "learned_entries": len(self.specialized_data),
            "connections": len(self.connections),
        }

    def search(self, query: str, limit: int = 3) -> List[Any]:
        """Search learned data for query."""
        q = query.lower()
        results = []
        for item in self.specialized_data:
            text = json.dumps(item).lower() if isinstance(item, dict) else str(item).lower()
            words = [w for w in q.split() if len(w) > 2]
            score = sum(1 for w in words if w in text)
            if score > 0:
                results.append((score, item))
        results.sort(key=lambda x: -x[0])
        return [item for _, item in results[:limit]]
