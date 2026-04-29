#!/usr/bin/env python3
"""
luo_cell.py — The Living Cell Base
====================================
The atomic unit of luo_memory. Every memory capability in the system
is a LuoCell subclass: self-contained, always alive, signal-driven.

Unlike a traditional module that waits to be called, a LuoCell:
  - runs as an asyncio coroutine in the background (always on)
  - fires signals to neighbors spontaneously when its threshold is crossed
  - has a lifespan and strength score that evolves with use
  - strengthens connections to cells it fires alongside (Hebb's law)
  - can detect its own corruption and request neighbor repair
  - divides into a child cell when its load exceeds capacity

Architecture
------------
  LuoCellNetwork          — the organism (holds all cells + message bus)
    └── LuoCell           — base class (this file)
          ├── EpisodicCell     — stores raw events with timestamp
          ├── SemanticCell     — promotes repeated episodes to facts
          ├── SkillCell        — crystallizes successful tool chains
          ├── WorkingCell      — in-session scratchpad, auto-flushes
          ├── DecayCell        — ticks continuously, weakens cold memories
          ├── DreamCell        — consolidates on idle (hippocampal replay)
          ├── ImportanceCell   — tags high-impact events to resist decay
          └── AssociativeCell  — spreads activation across linked memories

Created by Luo Kai (luokai25) as part of luo_memory v1.0
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("luo_memory")


# ─────────────────────────────────────────────
# Signal — the neurotransmitter between cells
# ─────────────────────────────────────────────

@dataclass
class Signal:
    """A message passed between luo-cells."""
    source: str          # cell_id of sender
    target: str          # cell_id of receiver ("*" = broadcast)
    signal_type: str     # e.g. "store", "search", "promote", "decay_tick"
    payload: Dict        # arbitrary data
    timestamp: float = field(default_factory=time.time)
    strength: float = 1.0  # signal strength (0.0–1.0), decays with hops


# ─────────────────────────────────────────────
# SynapseTable — persistent Hebbian weights
# ─────────────────────────────────────────────

class SynapseTable:
    """
    SQLite-backed table of connection weights between cells.
    Weight increases each time two cells fire within co_window seconds.
    This is Hebb's law: neurons that fire together, wire together.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS synapses (
                    cell_a      TEXT NOT NULL,
                    cell_b      TEXT NOT NULL,
                    weight      REAL DEFAULT 0.1,
                    fire_count  INTEGER DEFAULT 0,
                    last_fired  REAL DEFAULT 0,
                    PRIMARY KEY (cell_a, cell_b)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cell_registry (
                    cell_id     TEXT PRIMARY KEY,
                    cell_type   TEXT,
                    strength    REAL DEFAULT 1.0,
                    born_at     REAL,
                    last_active REAL,
                    fire_count  INTEGER DEFAULT 0,
                    metadata    TEXT DEFAULT '{}'
                )
            """)
            conn.commit()

    def strengthen(self, cell_a: str, cell_b: str, delta: float = 0.05):
        """Hebbian potentiation — called when two cells co-fire."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO synapses (cell_a, cell_b, weight, fire_count, last_fired)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(cell_a, cell_b) DO UPDATE SET
                    weight = MIN(1.0, weight + ?),
                    fire_count = fire_count + 1,
                    last_fired = ?
            """, (cell_a, cell_b, delta, time.time(), delta, time.time()))
            conn.commit()

    def weaken(self, cell_a: str, cell_b: str, delta: float = 0.01):
        """Hebbian depression — called by DecayCell on cold connections."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE synapses SET weight = MAX(0.0, weight - ?)
                WHERE cell_a = ? AND cell_b = ?
            """, (delta, cell_a, cell_b))
            conn.commit()

    def get_weight(self, cell_a: str, cell_b: str) -> float:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT weight FROM synapses WHERE cell_a=? AND cell_b=?",
                (cell_a, cell_b)
            ).fetchone()
            return row[0] if row else 0.0

    def get_neighbors(self, cell_id: str, min_weight: float = 0.1) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT cell_b, weight FROM synapses
                WHERE cell_a = ? AND weight >= ?
                ORDER BY weight DESC LIMIT 20
            """, (cell_id, min_weight)).fetchall()
            return [{"cell_id": r[0], "weight": r[1]} for r in rows]

    def register_cell(self, cell_id: str, cell_type: str, metadata: dict = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO cell_registry
                (cell_id, cell_type, strength, born_at, last_active, metadata)
                VALUES (?, ?, 1.0, ?, ?, ?)
            """, (cell_id, cell_type, time.time(), time.time(),
                  json.dumps(metadata or {})))
            conn.commit()

    def update_cell_activity(self, cell_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE cell_registry SET
                    last_active = ?,
                    fire_count = fire_count + 1
                WHERE cell_id = ?
            """, (time.time(), cell_id))
            conn.commit()

    def get_cell_strength(self, cell_id: str) -> float:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT strength FROM cell_registry WHERE cell_id=?",
                (cell_id,)
            ).fetchone()
            return row[0] if row else 1.0

    def set_cell_strength(self, cell_id: str, strength: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE cell_registry SET strength=? WHERE cell_id=?",
                (max(0.0, min(1.0, strength)), cell_id)
            )
            conn.commit()


# ─────────────────────────────────────────────
# LuoCell — base class
# ─────────────────────────────────────────────

class LuoCell(ABC):
    """
    Base class for all luo-cells.

    A cell is not called — it lives. It runs a background loop via
    asyncio and reacts to incoming signals on its inbox queue.
    It fires outgoing signals to the network bus spontaneously
    when its internal thresholds are crossed.

    Subclass this and implement:
      - on_signal(signal)  → async, handle an incoming signal
      - tick()             → async, called every tick_interval seconds
    """

    TICK_INTERVAL = 30.0    # seconds between background ticks
    CO_FIRE_WINDOW = 2.0    # seconds — if two cells fire within this, strengthen synapse
    MAX_INBOX = 256         # max buffered signals before dropping oldest

    def __init__(
        self,
        cell_id: str,
        cell_type: str,
        network: "LuoCellNetwork",
        palace_path: str,
    ):
        self.cell_id = cell_id
        self.cell_type = cell_type
        self.network = network
        self.palace_path = palace_path
        self.inbox: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_INBOX)
        self.strength: float = 1.0
        self.born_at: float = time.time()
        self.last_active: float = time.time()
        self.fire_count: int = 0
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

        # register in synapse table
        self.network.synapses.register_cell(cell_id, cell_type)
        logger.debug(f"[{self.cell_id}] born")

    # ── lifecycle ──────────────────────────────

    def start(self) -> asyncio.Task:
        """Start the cell's background loop."""
        self._running = True
        self._task = asyncio.get_event_loop().create_task(self._run())
        return self._task

    def stop(self):
        """Gracefully stop the cell."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run(self):
        """Main event loop: drain inbox + periodic tick."""
        last_tick = time.time()
        while self._running:
            try:
                # process all queued signals (non-blocking)
                while not self.inbox.empty():
                    signal = self.inbox.get_nowait()
                    await self._process_signal(signal)

                # periodic tick
                now = time.time()
                if now - last_tick >= self.TICK_INTERVAL:
                    await self._tick_wrapper()
                    last_tick = now

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.cell_id}] error in run loop: {e}")
                await asyncio.sleep(1.0)

    async def _process_signal(self, signal: Signal):
        try:
            self.last_active = time.time()
            self.fire_count += 1
            self.network.synapses.update_cell_activity(self.cell_id)

            # Hebbian potentiation: strengthen synapse to recent co-firers
            recent = self.network.get_recent_firers(
                exclude=self.cell_id,
                window=self.CO_FIRE_WINDOW
            )
            for co_cell_id in recent:
                self.network.synapses.strengthen(self.cell_id, co_cell_id)

            self.network.record_fire(self.cell_id)
            await self.on_signal(signal)

        except Exception as e:
            logger.error(f"[{self.cell_id}] error processing signal: {e}")

    async def _tick_wrapper(self):
        try:
            await self.tick()
        except Exception as e:
            logger.error(f"[{self.cell_id}] error in tick: {e}")

    # ── signaling ─────────────────────────────

    def fire(self, target: str, signal_type: str, payload: Dict, strength: float = 1.0):
        """Send a signal to another cell (or broadcast with target='*')."""
        signal = Signal(
            source=self.cell_id,
            target=target,
            signal_type=signal_type,
            payload=payload,
            strength=strength,
        )
        self.network.route(signal)

    def receive(self, signal: Signal):
        """Called by the network to deliver a signal to this cell's inbox."""
        try:
            self.inbox.put_nowait(signal)
        except asyncio.QueueFull:
            # drop oldest to make room
            try:
                self.inbox.get_nowait()
                self.inbox.put_nowait(signal)
            except Exception:
                pass

    # ── self-repair ───────────────────────────

    async def request_repair(self, reason: str):
        """Broadcast a repair request to neighbor cells."""
        logger.warning(f"[{self.cell_id}] requesting repair: {reason}")
        self.fire("*", "repair_request", {
            "damaged_cell": self.cell_id,
            "reason": reason,
            "timestamp": time.time(),
        })

    # ── abstract interface ────────────────────

    @abstractmethod
    async def on_signal(self, signal: Signal):
        """Handle an incoming signal. Must be implemented by subclasses."""
        ...

    async def tick(self):
        """Called every TICK_INTERVAL seconds. Override for background work."""
        pass

    # ── utility ───────────────────────────────

    def cell_path(self, *parts) -> Path:
        """Resolve a path inside this cell's palace wing."""
        p = Path(self.palace_path) / self.cell_type
        p.mkdir(parents=True, exist_ok=True)
        return p.joinpath(*parts) if parts else p

    def __repr__(self):
        return (
            f"<{self.cell_type}:{self.cell_id} "
            f"strength={self.strength:.2f} fires={self.fire_count}>"
        )


# ─────────────────────────────────────────────
# LuoCellNetwork — the organism
# ─────────────────────────────────────────────

class LuoCellNetwork:
    """
    The organism that holds all luo-cells and routes signals between them.

    This is the equivalent of the brain itself — not intelligent on its own,
    but the substrate through which cell interactions create intelligence.
    """

    def __init__(self, palace_path: str):
        self.palace_path = palace_path
        os.makedirs(palace_path, exist_ok=True)

        db_path = os.path.join(palace_path, "synapses.db")
        self.synapses = SynapseTable(db_path)

        self._cells: Dict[str, LuoCell] = {}
        self._fire_log: List[Dict] = []   # recent fires for Hebbian window
        self._lock = asyncio.Lock()

    def register(self, cell: LuoCell):
        """Add a cell to the network."""
        self._cells[cell.cell_id] = cell
        logger.info(f"[network] registered {cell}")

    def route(self, signal: Signal):
        """Route a signal to its target cell(s)."""
        if signal.target == "*":
            for cell in self._cells.values():
                if cell.cell_id != signal.source:
                    cell.receive(signal)
        elif signal.target in self._cells:
            self._cells[signal.target].receive(signal)
        else:
            logger.debug(
                f"[network] signal to unknown target '{signal.target}' dropped"
            )

    def record_fire(self, cell_id: str):
        """Log a cell firing for the Hebbian co-fire window."""
        self._fire_log.append({"cell_id": cell_id, "at": time.time()})
        # trim log to last 60 seconds
        cutoff = time.time() - 60
        self._fire_log = [e for e in self._fire_log if e["at"] > cutoff]

    def get_recent_firers(
        self, exclude: str, window: float = 2.0
    ) -> List[str]:
        """Return cell IDs that fired within the co-fire window."""
        cutoff = time.time() - window
        return [
            e["cell_id"] for e in self._fire_log
            if e["at"] > cutoff and e["cell_id"] != exclude
        ]

    def start_all(self):
        """Start all registered cells."""
        for cell in self._cells.values():
            cell.start()
        logger.info(f"[network] started {len(self._cells)} cells")

    def stop_all(self):
        """Stop all cells."""
        for cell in self._cells.values():
            cell.stop()

    def get(self, cell_id: str) -> Optional[LuoCell]:
        return self._cells.get(cell_id)

    def status(self) -> Dict:
        return {
            "cells": len(self._cells),
            "cell_list": [
                {
                    "id": c.cell_id,
                    "type": c.cell_type,
                    "strength": c.strength,
                    "fires": c.fire_count,
                    "alive": c._running,
                }
                for c in self._cells.values()
            ],
        }
