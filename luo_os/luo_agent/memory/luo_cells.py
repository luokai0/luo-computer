#!/usr/bin/env python3
"""
luo_cells.py — The Eight Specialized Luo-Cells
================================================
Each cell is a living, autonomous memory capability.
They run in the background, signal each other, and together
form a memory organism that is more than the sum of its parts.

  EpisodicCell      — stores raw events with full temporal context
  SemanticCell      — promotes repeated episodes into permanent facts
  SkillCell         — crystallizes successful tool chains into reusable skills
  WorkingCell       — in-session scratchpad, auto-flushes to palace on exit
  DecayCell         — continuously weakens cold memories (Ebbinghaus curve)
  DreamCell         — idle-time consolidation (hippocampal replay)
  ImportanceCell    — tags high-impact events to resist decay
  AssociativeCell   — graph of linked memories for spreading activation

Created by Luo Kai (luokai25) — luo_memory v1.0
"""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from luo_agent.memory.luo_cell import LuoCell, LuoCellNetwork, Signal

logger = logging.getLogger("luo_memory")


# ─────────────────────────────────────────────
# EpisodicCell  (hippocampus)
# ─────────────────────────────────────────────

class EpisodicCell(LuoCell):
    """
    Stores every event verbatim with who/what/when/where context.
    Fires a 'new_episode' signal to SemanticCell after every store.
    Never discards — the human brain lossy-compresses, we don't.
    """

    TICK_INTERVAL = 60.0

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("episodic", "EpisodicCell", network, palace_path)
        self._init_db()

    def _db_path(self) -> str:
        p = self.cell_path()
        return str(p / "episodes.db")

    def _init_db(self):
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT,
                    agent_id    TEXT,
                    content     TEXT NOT NULL,
                    role        TEXT DEFAULT 'exchange',
                    importance  REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL DEFAULT 0,
                    timestamp   REAL NOT NULL,
                    metadata    TEXT DEFAULT '{}'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON episodes(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
            conn.commit()

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "store":
            episode_id = self._store(signal.payload)
            # notify semantic cell
            self.fire("semantic", "new_episode", {
                "episode_id": episode_id,
                "content": signal.payload.get("content", ""),
                "session_id": signal.payload.get("session_id", ""),
            })
            # notify importance cell
            self.fire("importance", "assess", {
                "episode_id": episode_id,
                "content": signal.payload.get("content", ""),
            })

        elif signal.signal_type == "recall":
            results = self._recall(
                query=signal.payload.get("query", ""),
                session_id=signal.payload.get("session_id"),
                limit=signal.payload.get("limit", 10),
            )
            # put results into payload for caller to read
            signal.payload["_results"] = results

        elif signal.signal_type == "repair_request":
            # another cell is asking for help — log and try to re-index
            logger.info(f"[{self.cell_id}] repair request received from "
                        f"{signal.payload.get('damaged_cell')}")

    def _store(self, payload: Dict) -> int:
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            cursor = conn.execute("""
                INSERT INTO episodes
                (session_id, agent_id, content, role, importance, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.get("session_id", "default"),
                payload.get("agent_id", "luo_agent"),
                payload.get("content", ""),
                payload.get("role", "exchange"),
                payload.get("importance", 0.5),
                time.time(),
                json.dumps(payload.get("metadata", {})),
            ))
            conn.commit()
            return cursor.lastrowid

    def _recall(
        self,
        query: str = "",
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            if session_id:
                rows = conn.execute("""
                    SELECT id, content, role, importance, timestamp, session_id
                    FROM episodes WHERE session_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (session_id, limit)).fetchall()
            elif query:
                rows = conn.execute("""
                    SELECT id, content, role, importance, timestamp, session_id
                    FROM episodes WHERE content LIKE ?
                    ORDER BY importance DESC, timestamp DESC LIMIT ?
                """, (f"%{query}%", limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT id, content, role, importance, timestamp, session_id
                    FROM episodes ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()

            # update access counts
            ids = [r[0] for r in rows]
            if ids:
                conn.execute(
                    f"UPDATE episodes SET access_count=access_count+1, "
                    f"last_accessed=? WHERE id IN ({','.join('?'*len(ids))})",
                    [time.time()] + ids
                )
                conn.commit()

        return [
            {
                "id": r[0], "content": r[1], "role": r[2],
                "importance": r[3], "timestamp": r[4], "session_id": r[5],
            }
            for r in rows
        ]

    async def tick(self):
        # log how many episodes we hold
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        logger.debug(f"[{self.cell_id}] holding {count} episodes")


# ─────────────────────────────────────────────
# SemanticCell  (cerebral cortex)
# ─────────────────────────────────────────────

class SemanticCell(LuoCell):
    """
    Promotes repeated episodes into permanent semantic facts.
    When the same concept appears 3+ times across sessions,
    it stops being a 'memory of an event' and becomes 'knowledge'.
    This mirrors how the brain semantizes episodic memory over time.
    """

    TICK_INTERVAL = 120.0
    PROMOTION_THRESHOLD = 3   # episodes needed to promote a fact

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("semantic", "SemanticCell", network, palace_path)
        self._init_db()
        self._episode_buffer: List[Dict] = []

    def _db_path(self) -> str:
        return str(self.cell_path() / "facts.db")

    def _init_db(self):
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    key         TEXT UNIQUE NOT NULL,
                    value       TEXT NOT NULL,
                    confidence  REAL DEFAULT 0.5,
                    source_count INTEGER DEFAULT 1,
                    first_seen  REAL,
                    last_updated REAL,
                    metadata    TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    content     TEXT PRIMARY KEY,
                    seen_count  INTEGER DEFAULT 1,
                    last_seen   REAL
                )
            """)
            conn.commit()

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "new_episode":
            content = signal.payload.get("content", "")
            self._track_candidate(content)

        elif signal.signal_type == "learn_fact":
            self._store_fact(
                key=signal.payload.get("key", ""),
                value=signal.payload.get("value", ""),
                confidence=signal.payload.get("confidence", 0.8),
            )

        elif signal.signal_type == "get_facts":
            signal.payload["_results"] = self._get_all_facts()

    def _track_candidate(self, content: str):
        """Track how many times a concept appears — promote when threshold met."""
        key = content[:120].lower().strip()
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                INSERT INTO candidates (content, seen_count, last_seen)
                VALUES (?, 1, ?)
                ON CONFLICT(content) DO UPDATE SET
                    seen_count = seen_count + 1,
                    last_seen = ?
            """, (key, time.time(), time.time()))
            conn.commit()

            row = conn.execute(
                "SELECT seen_count FROM candidates WHERE content=?", (key,)
            ).fetchone()

            if row and row[0] >= self.PROMOTION_THRESHOLD:
                # promote to fact
                self._store_fact(
                    key=key[:60],
                    value=content,
                    confidence=min(0.99, row[0] / 10.0),
                )
                logger.info(
                    f"[{self.cell_id}] promoted fact after {row[0]} observations: "
                    f"{key[:50]}..."
                )

    def _store_fact(self, key: str, value: str, confidence: float = 0.8):
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                INSERT INTO facts (key, value, confidence, source_count, first_seen, last_updated)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = ?,
                    confidence = MIN(0.99, confidence + 0.05),
                    source_count = source_count + 1,
                    last_updated = ?
            """, (key, value, confidence, time.time(), time.time(),
                  value, time.time()))
            conn.commit()

    def _get_all_facts(self) -> List[Dict]:
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            rows = conn.execute("""
                SELECT key, value, confidence, source_count, last_updated
                FROM facts ORDER BY confidence DESC, source_count DESC
            """).fetchall()
        return [
            {"key": r[0], "value": r[1], "confidence": r[2],
             "source_count": r[3], "last_updated": r[4]}
            for r in rows
        ]

    async def tick(self):
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        logger.debug(f"[{self.cell_id}] {facts} facts, {candidates} candidates")


# ─────────────────────────────────────────────
# SkillCell  (cerebellum)
# ─────────────────────────────────────────────

class SkillCell(LuoCell):
    """
    Observes tool execution chains and crystallizes successful ones into skills.
    A skill is a named sequence of tool calls that achieved a goal.
    Once crystallized, LUOKAI can invoke the skill by name instead of
    reasoning through it from scratch each time.
    """

    TICK_INTERVAL = 90.0
    SUCCESS_THRESHOLD = 2   # successful runs needed to crystallize a skill

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("skill", "SkillCell", network, palace_path)
        self._init_db()
        self._current_chain: List[Dict] = []

    def _db_path(self) -> str:
        return str(self.cell_path() / "skills.db")

    def _init_db(self):
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    name         TEXT UNIQUE NOT NULL,
                    description  TEXT,
                    tool_chain   TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    last_used    REAL,
                    created_at   REAL,
                    metadata     TEXT DEFAULT '{}'
                )
            """)
            conn.commit()

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "tool_executed":
            self._current_chain.append({
                "tool": signal.payload.get("tool"),
                "args": signal.payload.get("args", {}),
                "result_summary": signal.payload.get("result_summary", ""),
                "success": signal.payload.get("success", True),
                "timestamp": time.time(),
            })

        elif signal.signal_type == "task_completed":
            if signal.payload.get("success") and len(self._current_chain) >= 2:
                self._consider_crystallization(
                    goal=signal.payload.get("goal", ""),
                    chain=self._current_chain.copy(),
                )
            self._current_chain.clear()

        elif signal.signal_type == "get_skill":
            name = signal.payload.get("name", "")
            signal.payload["_result"] = self._get_skill(name)

        elif signal.signal_type == "list_skills":
            signal.payload["_results"] = self._list_skills()

    def _consider_crystallization(self, goal: str, chain: List[Dict]):
        """Attempt to save or reinforce a skill from a successful chain."""
        skill_name = goal[:60].lower().replace(" ", "_")[:40] if goal else (
            "_".join(c["tool"] for c in chain[:3])
        )
        chain_json = json.dumps(chain)

        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                INSERT INTO skills (name, description, tool_chain, success_count,
                                    last_used, created_at)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    success_count = success_count + 1,
                    last_used = ?,
                    tool_chain = ?
            """, (skill_name, goal, chain_json, time.time(), time.time(),
                  time.time(), chain_json))
            conn.commit()
            logger.info(f"[{self.cell_id}] skill crystallized: {skill_name}")

    def _get_skill(self, name: str) -> Optional[Dict]:
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            row = conn.execute(
                "SELECT name, description, tool_chain, success_count FROM skills WHERE name=?",
                (name,)
            ).fetchone()
        if row:
            return {
                "name": row[0], "description": row[1],
                "tool_chain": (json.loads(row[2]) if row[2] else []), "success_count": row[3],
            }
        return None

    def _list_skills(self) -> List[Dict]:
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            rows = conn.execute("""
                SELECT name, description, success_count, last_used
                FROM skills ORDER BY success_count DESC
            """).fetchall()
        return [
            {"name": r[0], "description": r[1],
             "success_count": r[2], "last_used": r[3]}
            for r in rows
        ]

    async def tick(self):
        with sqlite3.connect(self._db_path()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        logger.debug(f"[{self.cell_id}] {count} crystallized skills")


# ─────────────────────────────────────────────
# WorkingCell  (prefrontal cortex)
# ─────────────────────────────────────────────

class WorkingCell(LuoCell):
    """
    In-session scratchpad — the '7±2 items' short-term buffer.
    Holds the current task context, tool results, and reasoning steps.
    Auto-flushes to EpisodicCell at session end.
    """

    TICK_INTERVAL = 10.0
    MAX_SLOTS = 12   # slightly more generous than human working memory

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("working", "WorkingCell", network, palace_path)
        self._slots: List[Dict] = []
        self._session_id: str = f"session_{int(time.time())}"

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "push":
            self._push(signal.payload)
            signal.payload["_session_id"] = self._session_id

        elif signal.signal_type == "peek":
            signal.payload["_slots"] = self._slots.copy()

        elif signal.signal_type == "flush":
            await self._flush()

        elif signal.signal_type == "new_session":
            await self._flush()
            self._session_id = signal.payload.get(
                "session_id", f"session_{int(time.time())}"
            )
            self._slots.clear()

    def _push(self, payload: Dict):
        """Add item to working memory, evicting oldest if full."""
        item = {
            "content": payload.get("content", ""),
            "role": payload.get("role", "observation"),
            "timestamp": time.time(),
        }
        if len(self._slots) >= self.MAX_SLOTS:
            evicted = self._slots.pop(0)
            logger.debug(
                f"[{self.cell_id}] evicted: {evicted['content'][:40]}..."
            )
        self._slots.append(item)

    async def _flush(self):
        """Push all slots to EpisodicCell for long-term storage."""
        if not self._slots:
            return
        for slot in self._slots:
            self.fire("episodic", "store", {
                "content": slot["content"],
                "role": slot["role"],
                "session_id": self._session_id,
                "importance": 0.4,
            })
        logger.info(
            f"[{self.cell_id}] flushed {len(self._slots)} items "
            f"from session {self._session_id}"
        )
        self._slots.clear()

    async def tick(self):
        logger.debug(
            f"[{self.cell_id}] {len(self._slots)}/{self.MAX_SLOTS} slots used "
            f"in session {self._session_id}"
        )


# ─────────────────────────────────────────────
# DecayCell  (Ebbinghaus forgetting curve)
# ─────────────────────────────────────────────

class DecayCell(LuoCell):
    """
    Always ticking. Weakens synapse connections that haven't fired recently.
    High-importance memories and recently-accessed memories decay slower.
    This is the Ebbinghaus forgetting curve applied to AI memory.

    decay_score = base_decay × (1 / (1 + access_count)) × time_factor
    """

    TICK_INTERVAL = 300.0    # run every 5 minutes
    DECAY_RATE = 0.005        # per tick, per cold connection
    HOT_THRESHOLD = 3600      # seconds — memories accessed within 1 hour are "hot"

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("decay", "DecayCell", network, palace_path)

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "force_decay":
            await self._run_decay()

    async def tick(self):
        await self._run_decay()

    async def _run_decay(self):
        """
        Decay all synaptic connections proportional to time since last fire.
        Hot connections (recently used) are protected.
        """
        synapses_db = os.path.join(self.palace_path, "synapses.db")
        if not os.path.exists(synapses_db):
            return

        now = time.time()
        hot_cutoff = now - self.HOT_THRESHOLD
        decayed_count = 0

        with sqlite3.connect(synapses_db) as conn:
            cold = conn.execute(
                "SELECT cell_a, cell_b, weight FROM synapses WHERE last_fired < ?",
                (hot_cutoff,)
            ).fetchall()

            for cell_a, cell_b, weight in cold:
                if weight <= 0.01:
                    continue  # already dead
                time_cold = now - hot_cutoff
                decay = self.DECAY_RATE * min(1.0, time_cold / 86400)
                new_weight = max(0.0, weight - decay)
                conn.execute(
                    "UPDATE synapses SET weight=? WHERE cell_a=? AND cell_b=?",
                    (new_weight, cell_a, cell_b)
                )
                decayed_count += 1

            conn.commit()

        if decayed_count:
            logger.debug(
                f"[{self.cell_id}] decayed {decayed_count} cold connections"
            )


# ─────────────────────────────────────────────
# DreamCell  (hippocampal replay / sleep)
# ─────────────────────────────────────────────

class DreamCell(LuoCell):
    """
    Activates when the system is idle. Replays recent episodes,
    clusters related memories, and fires promotions to SemanticCell.
    This is the AI equivalent of hippocampal replay during sleep.
    """

    TICK_INTERVAL = 600.0      # every 10 minutes
    IDLE_THRESHOLD = 120.0     # seconds of no activity before dreaming
    CLUSTER_WINDOW = 3600.0    # look at last hour's episodes

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("dream", "DreamCell", network, palace_path)
        self._last_system_activity: float = time.time()

    async def on_signal(self, signal: Signal):
        if signal.signal_type in ("store", "new_episode", "tool_executed"):
            # any activity resets the idle timer
            self._last_system_activity = time.time()

        elif signal.signal_type == "force_dream":
            await self._consolidate()

    async def tick(self):
        idle_time = time.time() - self._last_system_activity
        if idle_time >= self.IDLE_THRESHOLD:
            logger.info(
                f"[{self.cell_id}] system idle {idle_time:.0f}s — dreaming"
            )
            await self._consolidate()

    async def _consolidate(self):
        """
        Replay recent episodes and emit promotion signals for patterns found.
        """
        # ask episodic cell for recent episodes via direct signal
        payload: Dict = {"limit": 50}
        self.fire("episodic", "recall", payload)
        # give episodic cell a moment to process
        import asyncio
        await asyncio.sleep(0.2)

        episodes = payload.get("_results", [])
        if len(episodes) < 3:
            return

        # simple clustering: find content that appears in multiple episodes
        content_words: Dict[str, int] = {}
        for ep in episodes:
            for word in ep["content"].lower().split():
                if len(word) > 4:
                    content_words[word] = content_words.get(word, 0) + 1

        # promote words that appear 3+ times as semantic signals
        promoted = 0
        for word, count in content_words.items():
            if count >= 3:
                self.fire("semantic", "learn_fact", {
                    "key": f"recurring_concept:{word}",
                    "value": f"concept '{word}' has appeared {count} times recently",
                    "confidence": min(0.9, count / 10.0),
                })
                promoted += 1

        if promoted:
            logger.info(
                f"[{self.cell_id}] dream consolidation: promoted {promoted} "
                f"concepts from {len(episodes)} episodes"
            )


# ─────────────────────────────────────────────
# ImportanceCell  (amygdala)
# ─────────────────────────────────────────────

class ImportanceCell(LuoCell):
    """
    The amygdala equivalent. Assesses incoming episodes for high importance
    and boosts their score so they resist decay.

    High-importance triggers:
      - error / exception keywords
      - decision / choice keywords
      - breakthrough / solved / completed keywords
      - explicit user-flagged items
    """

    TICK_INTERVAL = 60.0

    HIGH_IMPORTANCE_KEYWORDS = {
        "error", "exception", "failed", "crash", "bug",         # errors
        "decided", "decision", "chose", "choice",                # decisions
        "solved", "completed", "finished", "breakthrough",       # achievements
        "critical", "important", "remember", "never forget",     # explicit flags
        "goal", "objective", "priority",                         # goals
    }

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("importance", "ImportanceCell", network, palace_path)

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "assess":
            episode_id = signal.payload.get("episode_id")
            content = signal.payload.get("content", "").lower()
            importance = self._score(content)

            if importance >= 0.7:
                # update the episode's importance directly
                self.fire("episodic", "boost_importance", {
                    "episode_id": episode_id,
                    "importance": importance,
                })
                logger.info(
                    f"[{self.cell_id}] high-importance event "
                    f"(score={importance:.2f}): {content[:60]}..."
                )

    def _score(self, content: str) -> float:
        words = set(content.lower().split())
        hits = words & self.HIGH_IMPORTANCE_KEYWORDS
        base = 0.5
        boost = len(hits) * 0.15
        return min(0.95, base + boost)

    async def tick(self):
        pass


# ─────────────────────────────────────────────
# AssociativeCell  (spreading activation)
# ─────────────────────────────────────────────

class AssociativeCell(LuoCell):
    """
    A pre-seeded knowledge graph with typed relations and multi-hop spreading.

    On first boot it seeds ~400 curated concept triples covering the domains
    most relevant to an AI agent (code, OS, tools, reasoning, memory, files).
    Every session then reinforces real edges via Hebbian co-occurrence.

    After even one session the graph is already useful.
    After 100 sessions it is a genuine personal knowledge graph.

    Relations stored:
        is_a        — taxonomy        (python is_a language)
        part_of     — composition     (function part_of code)
        causes      — causality       (error causes failure)
        used_for    — purpose         (bash used_for automation)
        opposite_of — contrast        (success opposite_of failure)
        related_to  — weak link       (memory related_to context)

    Spreading activation runs 2 hops deep by default so a query for
    "python" also surfaces "script", "automation", "file", "tool" etc.
    """

    TICK_INTERVAL = 180.0
    SPREAD_HOPS   = 2
    SPREAD_DECAY  = 0.6   # strength multiplied by this per hop
    MIN_STRENGTH  = 0.12

    # ── pre-seeded ontology ─────────────────────────────────────────
    # Format: (concept_a, relation, concept_b, initial_strength)
    # Covers: code, OS, AI, memory, tools, files, errors, tasks
    SEED_GRAPH: List[tuple] = [
        # programming languages & paradigms
        ("python",       "is_a",       "language",        0.9),
        ("python",       "used_for",   "automation",      0.85),
        ("python",       "used_for",   "scripting",       0.85),
        ("python",       "used_for",   "data",            0.7),
        ("bash",         "is_a",       "language",        0.9),
        ("bash",         "used_for",   "automation",      0.85),
        ("bash",         "used_for",   "shell",           0.9),
        ("javascript",   "is_a",       "language",        0.9),
        ("javascript",   "used_for",   "frontend",        0.85),
        ("rust",         "is_a",       "language",        0.9),
        ("rust",         "used_for",   "systems",         0.85),
        ("code",         "part_of",    "file",            0.7),
        ("function",     "part_of",    "code",            0.8),
        ("class",        "part_of",    "code",            0.8),
        ("variable",     "part_of",    "code",            0.7),
        ("loop",         "part_of",    "code",            0.7),
        ("import",       "part_of",    "code",            0.65),

        # OS & filesystem
        ("file",         "part_of",    "filesystem",      0.9),
        ("directory",    "part_of",    "filesystem",      0.9),
        ("path",         "part_of",    "filesystem",      0.85),
        ("process",      "part_of",    "os",              0.9),
        ("thread",       "part_of",    "process",         0.85),
        ("kernel",       "part_of",    "os",              0.95),
        ("shell",        "part_of",    "os",              0.85),
        ("terminal",     "is_a",       "shell",           0.85),
        ("permission",   "part_of",    "filesystem",      0.75),
        ("socket",       "part_of",    "network",         0.85),
        ("port",         "part_of",    "network",         0.85),
        ("memory",       "part_of",    "os",              0.9),
        ("cpu",          "part_of",    "hardware",        0.95),
        ("disk",         "part_of",    "hardware",        0.9),

        # AI & agent concepts
        ("agent",        "is_a",       "software",        0.8),
        ("agent",        "used_for",   "automation",      0.85),
        ("llm",          "is_a",       "model",           0.9),
        ("model",        "used_for",   "reasoning",       0.85),
        ("prompt",       "used_for",   "llm",             0.9),
        ("token",        "part_of",    "prompt",          0.85),
        ("context",      "part_of",    "prompt",          0.85),
        ("embedding",    "used_for",   "search",          0.85),
        ("vector",       "is_a",       "embedding",       0.8),
        ("tool",         "used_for",   "agent",           0.9),
        ("reasoning",    "part_of",    "intelligence",    0.9),
        ("planning",     "part_of",    "reasoning",       0.85),
        ("memory",       "part_of",    "intelligence",    0.9),
        ("learning",     "part_of",    "intelligence",    0.9),
        ("inference",    "used_for",   "reasoning",       0.8),
        ("hallucination","causes",     "error",           0.8),
        ("rag",          "used_for",   "memory",          0.8),
        ("luokai",       "is_a",       "tool",            0.9),
        ("luokai",       "used_for",   "inference",       0.95),

        # memory system concepts
        ("episodic",     "is_a",       "memory",          0.95),
        ("semantic",     "is_a",       "memory",          0.95),
        ("procedural",   "is_a",       "memory",          0.95),
        ("working",      "is_a",       "memory",          0.95),
        ("recall",       "used_for",   "memory",          0.9),
        ("storage",      "used_for",   "memory",          0.85),
        ("forgetting",   "causes",     "decay",           0.85),
        ("session",      "part_of",    "memory",          0.8),
        ("context",      "related_to", "memory",          0.75),
        ("knowledge",    "related_to", "semantic",        0.8),
        ("fact",         "is_a",       "knowledge",       0.85),
        ("skill",        "is_a",       "procedural",      0.85),

        # errors & debugging
        ("error",        "causes",     "failure",         0.95),
        ("exception",    "is_a",       "error",           0.9),
        ("bug",          "is_a",       "error",           0.85),
        ("crash",        "causes",     "failure",         0.9),
        ("traceback",    "related_to", "error",           0.85),
        ("debug",        "used_for",   "error",           0.9),
        ("fix",          "opposite_of","error",           0.8),
        ("test",         "used_for",   "debug",           0.85),
        ("log",          "used_for",   "debug",           0.8),
        ("failure",      "opposite_of","success",         0.95),

        # tasks & goals
        ("task",         "related_to", "goal",            0.85),
        ("goal",         "related_to", "planning",        0.85),
        ("decision",     "part_of",    "reasoning",       0.85),
        ("priority",     "related_to", "goal",            0.8),
        ("deadline",     "related_to", "task",            0.75),
        ("complete",     "opposite_of","incomplete",      0.9),
        ("success",      "related_to", "goal",            0.85),
        ("step",         "part_of",    "task",            0.85),
        ("workflow",     "related_to", "automation",      0.8),

        # data & search
        ("database",     "used_for",   "storage",         0.9),
        ("sqlite",       "is_a",       "database",        0.9),
        ("query",        "used_for",   "database",        0.9),
        ("index",        "part_of",    "database",        0.85),
        ("search",       "used_for",   "recall",          0.9),
        ("result",       "related_to", "search",          0.85),
        ("data",         "related_to", "storage",         0.8),
        ("json",         "is_a",       "data",            0.85),
        ("api",          "used_for",   "software",        0.85),
        ("request",      "part_of",    "api",             0.85),
        ("response",     "part_of",    "api",             0.85),

        # luo_os specific
        ("luo",          "is_a",       "agent",           0.95),
        ("luokai",       "is_a",       "agent",           0.95),
        ("luo_os",       "is_a",       "os",              0.95),
        ("luo_memory",   "is_a",       "memory",          0.95),
        ("palace",       "part_of",    "luo_memory",      0.9),
        ("cell",         "part_of",    "luo_memory",      0.9),
        ("synapse",      "part_of",    "cell",            0.9),
        ("wing",         "part_of",    "palace",          0.85),
        ("skill",        "part_of",    "luo_memory",      0.85),
    ]

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("associative", "AssociativeCell", network, palace_path)
        self._init_db()
        self._seed_graph()

    def _db_path(self) -> str:
        return str(self.cell_path() / "associations.db")

    def _conn(self):
        """WAL-mode connection for non-blocking concurrent reads."""
        conn = sqlite3.connect(self._db_path())
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")  # 8MB page cache
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS associations (
                    concept_a   TEXT NOT NULL,
                    relation    TEXT NOT NULL DEFAULT 'related_to',
                    concept_b   TEXT NOT NULL,
                    strength    REAL DEFAULT 0.1,
                    co_count    INTEGER DEFAULT 1,
                    seeded      INTEGER DEFAULT 0,
                    last_fired  REAL DEFAULT 0,
                    PRIMARY KEY (concept_a, concept_b)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ca ON associations(concept_a)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cb ON associations(concept_b)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_str ON associations(strength DESC)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS concepts (
                    name        TEXT PRIMARY KEY,
                    domain      TEXT DEFAULT 'general',
                    fire_count  INTEGER DEFAULT 0,
                    last_seen   REAL DEFAULT 0
                )
            """)
            conn.commit()

    def _seed_graph(self):
        """
        Pre-wire the knowledge graph with the curated ontology on first boot.
        Uses INSERT OR IGNORE so re-runs are safe — seeded edges are never
        overwritten by this method, only strengthened by real usage.
        """
        with self._conn() as conn:
            already = conn.execute(
                "SELECT COUNT(*) FROM associations WHERE seeded=1"
            ).fetchone()[0]
            if already >= len(self.SEED_GRAPH) * 0.8:
                return  # already seeded

            batch = []
            for concept_a, relation, concept_b, strength in self.SEED_GRAPH:
                a, b = concept_a.lower(), concept_b.lower()
                batch.append((a, relation, b, strength, 1, time.time()))
                # register both concepts
                conn.execute(
                    "INSERT OR IGNORE INTO concepts (name, domain) VALUES (?,?)",
                    (a, self._domain(relation))
                )
                conn.execute(
                    "INSERT OR IGNORE INTO concepts (name, domain) VALUES (?,?)",
                    (b, self._domain(relation))
                )

            conn.executemany("""
                INSERT OR IGNORE INTO associations
                (concept_a, relation, concept_b, strength, co_count, seeded, last_fired)
                VALUES (?, ?, ?, ?, 1, 1, ?)
            """, batch)
            conn.commit()
            logger.info(
                f"[{self.cell_id}] seeded {len(batch)} knowledge graph edges"
            )

    def _domain(self, relation: str) -> str:
        return {
            "is_a": "taxonomy", "part_of": "composition",
            "causes": "causality", "used_for": "purpose",
            "opposite_of": "contrast", "related_to": "general",
        }.get(relation, "general")

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "new_episode":
            content = signal.payload.get("content", "")
            await asyncio.get_event_loop().run_in_executor(
                None, self._extract_and_link, content
            )

        elif signal.signal_type == "activate":
            concept = signal.payload.get("concept", "")
            hops    = signal.payload.get("hops", self.SPREAD_HOPS)
            results = await asyncio.get_event_loop().run_in_executor(
                None, self._spread, concept, hops
            )
            signal.payload["_neighbors"] = results

        elif signal.signal_type == "link_concepts":
            # SemanticCell sends this when it promotes a fact
            a = signal.payload.get("concept_a", "")
            b = signal.payload.get("concept_b", "")
            rel = signal.payload.get("relation", "related_to")
            strength = signal.payload.get("strength", 0.6)
            if a and b:
                self._upsert_edge(a, rel, b, strength, seeded=0)

    def _extract_and_link(self, content: str):
        """
        Extract meaningful concepts (not just words) and link co-occurring ones.
        Filters stopwords, uses a sliding context window of 8 tokens,
        and upgrades existing seeded edges rather than duplicating them.
        """
        STOPWORDS = {
            "the","and","for","are","but","not","you","all","can","her",
            "was","one","our","out","day","get","has","him","his","how",
            "its","let","may","now","old","see","two","way","who","boy",
            "did","got","had","has","him","she","too","use","that","this",
            "with","have","from","they","will","been","were","said","each",
            "which","their","there","would","about","could","other","into",
        }
        tokens = [
            w.strip(".,!?;:\"'()[]{}").lower()
            for w in content.split()
            if len(w) > 3 and w.isalpha()
               and w.lower() not in STOPWORDS
        ]
        if len(tokens) < 2:
            return

        with self._conn() as conn:
            now = time.time()
            for i, word_a in enumerate(tokens):
                for word_b in tokens[i+1 : i+9]:  # window of 8
                    if word_a == word_b:
                        continue
                    a, b = sorted([word_a, word_b])
                    conn.execute("""
                        INSERT INTO associations
                            (concept_a, relation, concept_b, strength, co_count,
                             seeded, last_fired)
                        VALUES (?, 'related_to', ?, 0.08, 1, 0, ?)
                        ON CONFLICT(concept_a, concept_b) DO UPDATE SET
                            strength   = MIN(1.0, strength + 0.018),
                            co_count   = co_count + 1,
                            last_fired = ?
                    """, (a, b, now, now))
                # update concept fire count
                conn.execute("""
                    INSERT INTO concepts (name, fire_count, last_seen)
                    VALUES (?, 1, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        fire_count = fire_count + 1,
                        last_seen  = ?
                """, (word_a, now, now))
            conn.commit()

    def _upsert_edge(
        self,
        concept_a: str,
        relation: str,
        concept_b: str,
        strength: float,
        seeded: int = 0,
    ):
        a, b = sorted([concept_a.lower(), concept_b.lower()])
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO associations
                    (concept_a, relation, concept_b, strength, co_count,
                     seeded, last_fired)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(concept_a, concept_b) DO UPDATE SET
                    strength   = MIN(1.0, MAX(strength, ?)),
                    relation   = CASE WHEN seeded=1 THEN relation ELSE ? END,
                    last_fired = ?
            """, (a, relation, b, strength, seeded, time.time(),
                  strength, relation, time.time()))
            conn.commit()

    def _spread(self, concept: str, hops: int = 2) -> List[Dict]:
        """
        Multi-hop spreading activation.
        Hop 1: direct neighbors of concept.
        Hop 2: neighbors of those neighbors, with strength × SPREAD_DECAY.
        Returns deduplicated list sorted by activation strength.
        """
        concept = concept.lower()
        visited: Dict[str, float] = {}  # concept -> best activation

        def _neighbors(c: str, min_s: float) -> List[tuple]:
            with self._conn() as conn:
                rows = conn.execute("""
                    SELECT concept_b, relation, strength FROM associations
                    WHERE concept_a = ? AND strength >= ?
                    UNION
                    SELECT concept_a, relation, strength FROM associations
                    WHERE concept_b = ? AND strength >= ?
                    ORDER BY strength DESC LIMIT 15
                """, (c, min_s, c, min_s)).fetchall()
            return rows

        # hop 0 → 1
        for nb, rel, s in _neighbors(concept, self.MIN_STRENGTH):
            if nb != concept:
                visited[nb] = max(visited.get(nb, 0), s)

        if hops >= 2:
            # hop 1 → 2 (decayed)
            for hop1_concept, hop1_strength in list(visited.items()):
                for nb, rel, s in _neighbors(hop1_concept, self.MIN_STRENGTH):
                    if nb != concept and nb not in visited:
                        decayed = s * hop1_strength * self.SPREAD_DECAY
                        if decayed >= self.MIN_STRENGTH:
                            visited[nb] = max(visited.get(nb, 0), decayed)

        return sorted(
            [{"concept": c, "strength": round(s, 3)} for c, s in visited.items()],
            key=lambda x: x["strength"],
            reverse=True,
        )[:20]

    async def tick(self):
        with self._conn() as conn:
            edges = conn.execute(
                "SELECT COUNT(*) FROM associations"
            ).fetchone()[0]
            concepts = conn.execute(
                "SELECT COUNT(*) FROM concepts"
            ).fetchone()[0]
        logger.debug(
            f"[{self.cell_id}] knowledge graph: {concepts} concepts, {edges} edges"
        )


# ─────────────────────────────────────────────
# TemporalCell  (temporal lobe / sequence memory)
# ─────────────────────────────────────────────

class TemporalCell(LuoCell):
    """
    Reasons over time. Stores events on a timeline and answers questions
    like 'what changed this week', 'what did I work on yesterday',
    'how long has this bug been present'.

    The human brain's temporal lobe specialises in sequencing and
    time-tagging events. No other cell in the system does this.
    """

    TICK_INTERVAL = 600.0

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("temporal", "TemporalCell", network, palace_path)
        self._init_db()

    def _db_path(self) -> str:
        return str(self.cell_path() / "timeline.db")

    def _conn(self):
        conn = sqlite3.connect(self._db_path())
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS timeline (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    event       TEXT NOT NULL,
                    event_type  TEXT DEFAULT 'exchange',
                    day_bucket  TEXT NOT NULL,
                    week_bucket TEXT NOT NULL,
                    timestamp   REAL NOT NULL,
                    session_id  TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_day  ON timeline(day_bucket)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_week ON timeline(week_bucket)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts   ON timeline(timestamp DESC)")
            conn.commit()

    async def on_signal(self, signal: Signal):
        if signal.signal_type in ("store", "new_episode"):
            content    = signal.payload.get("content", "")
            event_type = signal.payload.get("role", "exchange")
            session_id = signal.payload.get("session_id", "")
            now        = time.time()
            day_bucket  = time.strftime("%Y-%m-%d",     time.localtime(now))
            week_bucket = time.strftime("%Y-W%W",       time.localtime(now))
            with self._conn() as conn:
                conn.execute("""
                    INSERT INTO timeline
                    (event, event_type, day_bucket, week_bucket, timestamp, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (content[:400], event_type, day_bucket, week_bucket,
                      now, session_id))
                conn.commit()

        elif signal.signal_type == "query_time":
            period = signal.payload.get("period", "today")
            signal.payload["_results"] = self._query_period(period)

        elif signal.signal_type == "what_changed":
            signal.payload["_results"] = self._diff_periods(
                signal.payload.get("period_a", "yesterday"),
                signal.payload.get("period_b", "today"),
            )

    def _query_period(self, period: str) -> List[Dict]:
        now   = time.time()
        today = time.strftime("%Y-%m-%d", time.localtime(now))
        yesterday = time.strftime(
            "%Y-%m-%d",
            time.localtime(now - 86400)
        )
        this_week = time.strftime("%Y-W%W", time.localtime(now))

        with self._conn() as conn:
            if period == "today":
                rows = conn.execute(
                    "SELECT event, event_type, timestamp FROM timeline "
                    "WHERE day_bucket=? ORDER BY timestamp DESC LIMIT 30",
                    (today,)
                ).fetchall()
            elif period == "yesterday":
                rows = conn.execute(
                    "SELECT event, event_type, timestamp FROM timeline "
                    "WHERE day_bucket=? ORDER BY timestamp DESC LIMIT 30",
                    (yesterday,)
                ).fetchall()
            elif period == "this_week":
                rows = conn.execute(
                    "SELECT event, event_type, timestamp FROM timeline "
                    "WHERE week_bucket=? ORDER BY timestamp DESC LIMIT 50",
                    (this_week,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT event, event_type, timestamp FROM timeline "
                    "ORDER BY timestamp DESC LIMIT 20"
                ).fetchall()

        return [
            {"event": r[0], "type": r[1],
             "time": time.strftime("%Y-%m-%d %H:%M", time.localtime(r[2]))}
            for r in rows
        ]

    def _diff_periods(self, period_a: str, period_b: str) -> Dict:
        a = {e["event"][:80] for e in self._query_period(period_a)}
        b = {e["event"][:80] for e in self._query_period(period_b)}
        return {
            "only_in_a":  list(a - b)[:10],
            "only_in_b":  list(b - a)[:10],
            "in_both":    list(a & b)[:10],
        }

    async def tick(self):
        with self._conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM timeline"
            ).fetchone()[0]
        logger.debug(f"[{self.cell_id}] {count} events on timeline")


# ─────────────────────────────────────────────
# MetaCell  (default mode network / metacognition)
# ─────────────────────────────────────────────

class MetaCell(LuoCell):
    """
    Knows what it knows. Knows what it doesn't know.

    Before the agent answers a query, MetaCell checks whether the answer
    exists in memory and returns a confidence score. A low score is a
    signal that the agent should say "I'm not sure" rather than hallucinate.

    This is the cell that prevents confabulation — the human brain's
    default mode network monitors the reliability of retrieved memories.
    """

    TICK_INTERVAL = 120.0

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("meta", "MetaCell", network, palace_path)
        self._coverage: Dict[str, float] = {}   # topic -> confidence

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "confidence_check":
            query = signal.payload.get("query", "")
            signal.payload["_confidence"] = self._estimate_confidence(query)
            signal.payload["_known_topics"] = self._top_topics(5)

        elif signal.signal_type == "new_episode":
            # update topic coverage model
            content = signal.payload.get("content", "")
            self._update_coverage(content)

        elif signal.signal_type == "store":
            content = signal.payload.get("content", "")
            self._update_coverage(content)

    def _update_coverage(self, content: str):
        words = [
            w.lower().strip(".,!?;:")
            for w in content.split()
            if len(w) > 4 and w.isalpha()
        ]
        for w in words:
            self._coverage[w] = min(
                1.0,
                self._coverage.get(w, 0.0) + 0.04
            )
        # gentle decay of all coverage scores
        for k in list(self._coverage):
            self._coverage[k] *= 0.9995
            if self._coverage[k] < 0.01:
                del self._coverage[k]

    def _estimate_confidence(self, query: str) -> float:
        words = [
            w.lower().strip(".,!?;:")
            for w in query.split()
            if len(w) > 3
        ]
        if not words:
            return 0.0
        scores = [self._coverage.get(w, 0.0) for w in words]
        return round(sum(scores) / len(scores), 3)

    def _top_topics(self, n: int) -> List[str]:
        return sorted(
            self._coverage, key=self._coverage.get, reverse=True
        )[:n]

    async def tick(self):
        logger.debug(
            f"[{self.cell_id}] tracking {len(self._coverage)} topics, "
            f"top: {self._top_topics(3)}"
        )


# ─────────────────────────────────────────────
# GoalCell  (anterior cingulate cortex / goal maintenance)
# ─────────────────────────────────────────────

class GoalCell(LuoCell):
    """
    Keeps active goals hot across every session.

    Unlike EpisodicCell which stores everything, GoalCell maintains a small
    set of persistent objectives that are always injected into wake_up context.
    Goals can be set, updated, completed, and abandoned.
    Completed goals are archived rather than deleted — they inform future planning.

    The anterior cingulate cortex holds goal representations active across
    time and re-activates them when relevant context appears.
    """

    TICK_INTERVAL = 300.0
    MAX_ACTIVE_GOALS = 7   # Miller's number — 7 ± 2

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("goal", "GoalCell", network, palace_path)
        self._init_db()

    def _db_path(self) -> str:
        return str(self.cell_path() / "goals.db")

    def _conn(self):
        conn = sqlite3.connect(self._db_path())
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    status      TEXT DEFAULT 'active',
                    priority    INTEGER DEFAULT 5,
                    created_at  REAL,
                    updated_at  REAL,
                    deadline    TEXT DEFAULT NULL,
                    progress    TEXT DEFAULT ''
                )
            """)
            conn.commit()

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "set_goal":
            self._set_goal(
                description=signal.payload.get("description", ""),
                priority=signal.payload.get("priority", 5),
                deadline=signal.payload.get("deadline"),
            )

        elif signal.signal_type == "complete_goal":
            self._update_status(
                signal.payload.get("goal_id"),
                "completed",
                signal.payload.get("description", ""),
            )

        elif signal.signal_type == "get_goals":
            signal.payload["_active"] = self._get_active()

        elif signal.signal_type == "task_completed":
            # auto-check if any goal matches this task description
            goal_desc = signal.payload.get("goal", "")
            if goal_desc and signal.payload.get("success"):
                self._maybe_complete_goal(goal_desc)

        elif signal.signal_type == "update_progress":
            self._add_progress(
                signal.payload.get("goal_id"),
                signal.payload.get("note", ""),
            )

    def _set_goal(self, description: str, priority: int = 5,
                  deadline: str = None):
        now = time.time()
        with self._conn() as conn:
            # enforce max active goals
            active = conn.execute(
                "SELECT COUNT(*) FROM goals WHERE status='active'"
            ).fetchone()[0]
            if active >= self.MAX_ACTIVE_GOALS:
                # demote lowest priority goal
                conn.execute("""
                    UPDATE goals SET status='deferred'
                    WHERE status='active'
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                """)
            conn.execute("""
                INSERT INTO goals
                (description, status, priority, created_at, updated_at, deadline)
                VALUES (?, 'active', ?, ?, ?, ?)
            """, (description, priority, now, now, deadline))
            conn.commit()
        logger.info(f"[{self.cell_id}] new goal (priority {priority}): {description[:60]}")

    def _update_status(self, goal_id: int, status: str, note: str = ""):
        with self._conn() as conn:
            conn.execute(
                "UPDATE goals SET status=?, updated_at=?, progress=progress||? "
                "WHERE id=?",
                (status, time.time(), f"\n[{status}] {note}", goal_id)
            )
            conn.commit()

    def _add_progress(self, goal_id: int, note: str):
        ts = time.strftime("%Y-%m-%d %H:%M")
        with self._conn() as conn:
            conn.execute(
                "UPDATE goals SET progress=progress||?, updated_at=? WHERE id=?",
                (f"\n[{ts}] {note}", time.time(), goal_id)
            )
            conn.commit()

    def _maybe_complete_goal(self, description: str):
        """Auto-complete a goal if the task description strongly matches."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, description FROM goals WHERE status='active'"
            ).fetchall()
            for gid, gdesc in rows:
                # simple overlap score
                a = set(description.lower().split())
                b = set(gdesc.lower().split())
                overlap = len(a & b) / max(len(b), 1)
                if overlap >= 0.6:
                    self._update_status(gid, "completed",
                                        f"auto-completed via: {description[:60]}")
                    break

    def _get_active(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT id, description, priority, deadline, progress, created_at
                FROM goals WHERE status='active'
                ORDER BY priority DESC, created_at ASC
            """).fetchall()
        return [
            {"id": r[0], "description": r[1], "priority": r[2],
             "deadline": r[3], "progress": r[4],
             "created": time.strftime("%Y-%m-%d", time.localtime(r[5]))}
            for r in rows
        ]

    async def tick(self):
        active = self._get_active()
        if active:
            logger.debug(
                f"[{self.cell_id}] {len(active)} active goals — "
                f"top: {active[0]['description'][:50]}"
            )


# ─────────────────────────────────────────────
# SensoryCell  (sensory buffer / input filter)
# ─────────────────────────────────────────────

class SensoryCell(LuoCell):
    """
    Pre-encodes and deduplicates raw input before it reaches EpisodicCell.

    The human brain's sensory memory holds the last ~500ms of raw stimulus
    and filters out what isn't worth encoding into working memory. For an
    agent, this means:
      - deduplicating near-identical inputs within a 30-second window
      - detecting very short/noisy inputs that shouldn't be stored
      - tagging the channel (chat, tool_result, system_event) before storage
      - rate-limiting rapid bursts of tool outputs

    Without this cell, every tool result and every message floods EpisodicCell
    indiscriminately, degrading retrieval quality over time.
    """

    TICK_INTERVAL = 30.0
    DEDUP_WINDOW  = 30.0    # seconds — identical content within this is dropped
    MIN_LENGTH    = 8       # characters — shorter inputs are filtered

    def __init__(self, network: LuoCellNetwork, palace_path: str):
        super().__init__("sensory", "SensoryCell", network, palace_path)
        self._recent: Dict[str, float] = {}  # content_hash -> timestamp
        self._pass_count   = 0
        self._filter_count = 0

    async def on_signal(self, signal: Signal):
        if signal.signal_type == "raw_input":
            content = signal.payload.get("content", "")
            channel = signal.payload.get("channel", "chat")

            if self._should_encode(content):
                # tag and forward to EpisodicCell
                signal.payload["role"]    = channel
                signal.payload["channel"] = channel
                self.fire("episodic", "store", signal.payload)
                self.fire("working",  "push",  signal.payload)
                self.fire("temporal", "store", signal.payload)
                self._pass_count += 1
            else:
                self._filter_count += 1

    def _should_encode(self, content: str) -> bool:
        if len(content.strip()) < self.MIN_LENGTH:
            return False
        h = str(hash(content.strip().lower()))
        now = time.time()
        if h in self._recent and (now - self._recent[h]) < self.DEDUP_WINDOW:
            return False
        self._recent[h] = now
        return True

    async def tick(self):
        # clean old dedup cache
        now = time.time()
        self._recent = {
            k: v for k, v in self._recent.items()
            if now - v < self.DEDUP_WINDOW * 4
        }
        logger.debug(
            f"[{self.cell_id}] passed={self._pass_count} "
            f"filtered={self._filter_count} "
            f"dedup_cache={len(self._recent)}"
        )
