#!/usr/bin/env python3
"""
luokai/data/loader.py — LUOKAI Data Integration Layer
======================================================
Loads all conversation and knowledge datasets into LUOKAI's inference engine.

Datasets integrated:
  sales/         — 3,411 sales conversations (goendalf666/sales-conversations)
  conversations/ — DailyDialog patterns, Task-Oriented dialogs, CCPE preferences
  coding/        — 971 coding Q&A pairs from skills library
  knowledge/     — semantic fact extracts

All data is indexed at startup for fast retrieval.
LUOKAI uses this to generate grounded, knowledge-rich responses.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA_ROOT = Path(__file__).parent


class DataLoader:
    """
    Loads and indexes all LUOKAI training data.
    Provides fast search across all datasets.
    """

    def __init__(self):
        self._sales:    List[Dict] = []   # 3,411 sales conversations
        self._daily:    List[Dict] = []   # Daily dialogue patterns
        self._task:     List[Dict] = []   # Task-oriented dialogs
        self._ccpe:     List[Dict] = []   # Preference conversations
        self._coding_qa: List[Dict] = []  # 971 coding Q&A pairs
        self._coding_conv: List[Dict] = [] # Coding conversations
        self._loaded = False

    def load(self):
        """Load all datasets. Called once at brain startup."""
        if self._loaded:
            return

        self._load_json("sales/sales_conversations.json",        self._sales)
        self._load_json("conversations/dailydialog_patterns.json", self._daily)
        self._load_json("conversations/task_oriented_dialogs.json", self._task)
        self._load_json("conversations/ccpe_preference_dialogs.json", self._ccpe)
        self._load_json("coding/coding_qa_from_skills.json",     self._coding_qa)
        self._load_json("coding/coding_conversations.json",       self._coding_conv)

        self._loaded = True
        total = (len(self._sales) + len(self._daily) + len(self._task) +
                 len(self._ccpe) + len(self._coding_qa))
        print(f"[DataLoader] ✅ Loaded {total:,} data entries")
        print(f"  Sales conversations:  {len(self._sales):,}")
        print(f"  Daily dialogues:      {len(self._daily)}")
        print(f"  Task dialogs:         {len(self._task)}")
        print(f"  Preference dialogs:   {len(self._ccpe)}")
        print(f"  Coding Q&A:          {len(self._coding_qa)}")

    def _load_json(self, rel_path: str, target: List):
        """Load a JSON file into target list."""
        path = DATA_ROOT / rel_path
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    target.extend(data)
            except Exception as e:
                print(f"[DataLoader] Warning: could not load {rel_path}: {e}")

    # ── Search APIs ───────────────────────────────────────────────────

    def search_sales(self, query: str, limit: int = 3) -> List[Dict]:
        """Find relevant sales conversation patterns."""
        if not self._loaded:
            self.load()
        return self._search_conversations(query, self._sales, limit)

    def search_coding(self, query: str, limit: int = 5) -> List[Dict]:
        """Find relevant coding Q&A pairs."""
        if not self._loaded:
            self.load()
        q = query.lower()
        scored = []
        for item in self._coding_qa:
            question = item.get('question', '').lower()
            answer   = item.get('answer', '').lower()
            cat      = item.get('category', '').lower()
            score = 0
            for term in q.split():
                if len(term) < 3:
                    continue
                if term in question: score += 5
                if term in answer:   score += 2
                if term in cat:      score += 3
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:limit]]

    def search_daily(self, query: str, limit: int = 3) -> List[Dict]:
        """Find relevant daily conversation patterns."""
        if not self._loaded:
            self.load()
        return self._search_conversations(query, self._daily + self._ccpe, limit)

    def search_task(self, query: str, limit: int = 3) -> List[Dict]:
        """Find relevant task-oriented conversation patterns."""
        if not self._loaded:
            self.load()
        return self._search_conversations(query, self._task, limit)

    def search_all(self, query: str, limit: int = 5) -> List[Dict]:
        """Search across all datasets."""
        if not self._loaded:
            self.load()
        all_convs = self._sales + self._daily + self._task + self._ccpe + self._coding_conv
        return self._search_conversations(query, all_convs, limit)

    def get_best_response(self, query: str) -> Optional[str]:
        """
        Find the best matching assistant response from all data.
        Returns the response text if a good match is found, else None.
        """
        if not self._loaded:
            self.load()

        # 1. Try coding Q&A first (most structured)
        coding = self.search_coding(query, limit=1)
        if coding and len(query.split()) >= 3:
            return coding[0].get('answer', '')

        # 2. Try all conversations
        results = self.search_all(query, limit=3)
        if not results:
            return None

        # Find the closest user turn and return its paired assistant response
        q_lower = query.lower()
        q_words = set(q_lower.split())

        best_score = 0
        best_response = None

        for conv in results:
            turns = conv.get('turns', [])
            for i, turn in enumerate(turns):
                if turn.get('role') != 'user':
                    continue
                content = turn.get('content', '').lower()
                c_words = set(content.split())
                overlap = len(q_words & c_words)
                # Require meaningful overlap
                if overlap >= 2 and overlap > best_score:
                    # Get the following assistant turn
                    if i + 1 < len(turns) and turns[i+1].get('role') == 'assistant':
                        best_score = overlap
                        best_response = turns[i+1].get('content', '')

        return best_response if best_score >= 2 else None

    def stats(self) -> Dict:
        """Return dataset statistics."""
        if not self._loaded:
            self.load()
        return {
            "sales_conversations": len(self._sales),
            "daily_dialogs":       len(self._daily),
            "task_dialogs":        len(self._task),
            "preference_dialogs":  len(self._ccpe),
            "coding_qa_pairs":     len(self._coding_qa),
            "coding_conversations":len(self._coding_conv),
            "total": (len(self._sales) + len(self._daily) + len(self._task) +
                      len(self._ccpe) + len(self._coding_qa) + len(self._coding_conv)),
        }

    def _search_conversations(self, query: str, pool: List[Dict], limit: int) -> List[Dict]:
        """Generic conversation search by term overlap."""
        q_lower = query.lower()
        terms   = [w for w in re.sub(r'[^\w\s]', '', q_lower).split() if len(w) > 2]
        if not terms:
            return []

        scored = []
        for conv in pool:
            score = 0
            # Score each turn
            for turn in conv.get('turns', []):
                content = turn.get('content', '').lower()
                for term in terms:
                    if term in content:
                        score += 2 if turn.get('role') == 'user' else 1
            # Score metadata
            for field in ('domain', 'topic', 'type', 'source', 'category'):
                val = conv.get(field, '').lower()
                for term in terms:
                    if term in val:
                        score += 3
            if score > 0:
                scored.append((score, conv))

        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:limit]]


# ── Module-level singleton ────────────────────────────────────────────
_loader: Optional[DataLoader] = None


def get_loader() -> DataLoader:
    """Get or create the singleton DataLoader."""
    global _loader
    if _loader is None:
        _loader = DataLoader()
        _loader.load()
    return _loader
