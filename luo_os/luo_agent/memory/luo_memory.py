#!/usr/bin/env python3
"""
luo_memory.py — Public API for the luo_memory Cell System
===========================================================
This is the single entry point for all memory operations in luo_os.

Usage
-----
    from luo_agent.memory.luo_memory import LuoMemory

    mem = LuoMemory()
    await mem.start()

    # store something
    await mem.store("The user prefers Python over Bash for automation")

    # recall semantically
    results = await mem.recall("what does the user prefer")

    # get hot context for next LLM prompt
    context = await mem.wake_up()

    # tell the system a task completed
    await mem.task_completed(goal="fix the api bug", success=True)

    # shut down gracefully (flushes working memory)
    await mem.stop()

Architecture
------------
LuoMemory boots a LuoCellNetwork and registers all 8 specialized cells.
All cells run as asyncio background tasks — they are always alive.
This file provides a clean synchronous-friendly API over the async cell bus.

Created by Luo Kai (luokai25) — luo_memory v1.0
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("luo_memory")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def _get_palace_path() -> str:
    """Default palace location: ~/.luo_memory/palace"""
    return os.path.expanduser(
        os.environ.get("LUO_PALACE_PATH", "~/.luo_memory/palace")
    )


class LuoMemory:
    """
    The luo_memory public interface.

    Boots the full cell network and exposes a clean API for:
      - storing memories
      - recalling by semantic search or keyword
      - loading hot context at session start
      - tracking tool executions for skill crystallization
      - triggering dream consolidation manually
      - inspecting network status
    """

    VERSION = "2.0.0"

    def __init__(self, palace_path: Optional[str] = None):
        self.palace_path = palace_path or _get_palace_path()
        os.makedirs(self.palace_path, exist_ok=True)

        # import here to allow luo_memory.py to be used standalone
        from luo_agent.memory.luo_cell import LuoCellNetwork
        from luo_agent.memory.luo_cells import (
            EpisodicCell, SemanticCell, SkillCell, WorkingCell,
            DecayCell, DreamCell, ImportanceCell, AssociativeCell,
            TemporalCell, MetaCell, GoalCell, SensoryCell,
        )

        self.network = LuoCellNetwork(self.palace_path)

        # instantiate all 12 cells
        self._episodic    = EpisodicCell(self.network, self.palace_path)
        self._semantic    = SemanticCell(self.network, self.palace_path)
        self._skill       = SkillCell(self.network, self.palace_path)
        self._working     = WorkingCell(self.network, self.palace_path)
        self._decay       = DecayCell(self.network, self.palace_path)
        self._dream       = DreamCell(self.network, self.palace_path)
        self._importance  = ImportanceCell(self.network, self.palace_path)
        self._associative = AssociativeCell(self.network, self.palace_path)
        self._temporal    = TemporalCell(self.network, self.palace_path)
        self._meta        = MetaCell(self.network, self.palace_path)
        self._goal        = GoalCell(self.network, self.palace_path)
        self._sensory     = SensoryCell(self.network, self.palace_path)

        # register all 12 cells with the network
        for cell in [
            self._episodic, self._semantic, self._skill, self._working,
            self._decay, self._dream, self._importance, self._associative,
            self._temporal, self._meta, self._goal, self._sensory,
        ]:
            self.network.register(cell)

        self._session_id: str = f"session_{int(time.time())}"
        self._started: bool = False

    # ── lifecycle ──────────────────────────────────────────────────────

    async def start(self, session_id: Optional[str] = None):
        """Boot the cell network. Call once at agent startup."""
        if self._started:
            return
        self.network.start_all()
        self._started = True

        if session_id:
            self._session_id = session_id

        # notify working cell of new session
        self._working.receive(
            __import__('luo_cell').Signal(
                source="luo_memory",
                target="working",
                signal_type="new_session",
                payload={"session_id": self._session_id},
            )
        )
        logger.info(
            f"[luo_memory v{self.VERSION}] cell network started — "
            f"session {self._session_id}"
        )

    async def stop(self):
        """Gracefully shut down: flush working memory then stop all cells."""
        if not self._started:
            return
        # flush working memory to episodic storage
        flush_signal = __import__('luo_cell').Signal(
            source="luo_memory",
            target="working",
            signal_type="flush",
            payload={},
        )
        self._working.receive(flush_signal)
        await asyncio.sleep(0.5)  # let flush process
        self.network.stop_all()
        self._started = False
        logger.info("[luo_memory] shut down cleanly")

    # ── core operations ────────────────────────────────────────────────

    async def store(
        self,
        content: str,
        role: str = "exchange",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
        wing: str = "luo_agent",
    ) -> bool:
        """
        Store a memory verbatim.

        Args:
            content:    The text to remember (stored exactly as given)
            role:       'exchange', 'observation', 'decision', 'skill_result'
            importance: 0.0–1.0 (ImportanceCell may override upward)
            metadata:   Any extra context dict
            wing:       Palace namespace ('luo_agent', 'user', 'skills')

        Returns:
            True on success
        """
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        signal = Signal(
            source="luo_memory",
            target="episodic",
            signal_type="store",
            payload={
                "content": content,
                "role": role,
                "importance": importance,
                "session_id": self._session_id,
                "agent_id": wing,
                "metadata": metadata or {},
            },
        )
        self._episodic.receive(signal)

        # also push to working memory scratchpad
        self._working.receive(Signal(
            source="luo_memory",
            target="working",
            signal_type="push",
            payload={"content": content, "role": role},
        ))
        return True

    async def recall(
        self,
        query: str = "",
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Recall memories by keyword search or session.

        For semantic (vector) search, use recall_semantic() instead.
        This uses fast SQLite text matching.
        """
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        payload: Dict = {
            "query": query,
            "session_id": session_id or self._session_id,
            "limit": limit,
        }
        signal = Signal(
            source="luo_memory",
            target="episodic",
            signal_type="recall",
            payload=payload,
        )
        self._episodic.receive(signal)
        await asyncio.sleep(0.15)  # allow async processing
        return payload.get("_results", [])

    async def get_facts(self) -> List[Dict]:
        """Return all promoted semantic facts."""
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        payload: Dict = {}
        self._semantic.receive(Signal(
            source="luo_memory",
            target="semantic",
            signal_type="get_facts",
            payload=payload,
        ))
        await asyncio.sleep(0.15)
        return payload.get("_results", [])

    async def learn_fact(self, key: str, value: str, confidence: float = 0.9):
        """Directly store a semantic fact (bypasses promotion threshold)."""
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        self._semantic.receive(Signal(
            source="luo_memory",
            target="semantic",
            signal_type="learn_fact",
            payload={"key": key, "value": value, "confidence": confidence},
        ))

    # ── wake-up context ────────────────────────────────────────────────

    async def wake_up(self, max_tokens: int = 2000) -> str:
        """
        Load hot context at the start of a session.
        Returns a formatted string ready to inject into the system prompt.

        Layers loaded:
          L0 — active goals (GoalCell)
          L1 — top semantic facts (SemanticCell)
          L2 — recent high-importance episodes (EpisodicCell)
          L3 — today's timeline summary (TemporalCell)
        """
        facts   = await self.get_facts()
        recent  = await self.recall(limit=8)
        goals   = await self.get_goals()
        today   = await self.query_time("today")

        lines = ["=== luo_memory context ==="]

        if goals:
            lines.append("\n[active goals]")
            for g in goals[:5]:
                deadline = f" (deadline: {g['deadline']})" if g.get("deadline") else ""
                lines.append(f"  [{g['priority']}] {g['description'][:100]}{deadline}")

        if facts:
            lines.append("\n[known facts]")
            for f in facts[:8]:
                lines.append(f"  • {f['key']}: {f['value'][:100]}")

        if recent:
            lines.append("\n[recent memory]")
            for ep in recent[-5:]:
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(ep["timestamp"]))
                lines.append(f"  [{ts}] {ep['content'][:120]}")

        if today:
            lines.append(f"\n[today: {len(today)} events]")
            for ev in today[:3]:
                lines.append(f"  {ev['time']} — {ev['event'][:80]}")

        lines.append("=========================")
        context = "\n".join(lines)

        max_chars = max_tokens * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "\n[...truncated]"

        logger.info(
            f"[luo_memory] wake_up: {len(goals)} goals, {len(facts)} facts, "
            f"{len(recent)} episodes, {len(today)} today events"
        )
        return context

    # ── skill tracking ─────────────────────────────────────────────────

    async def tool_executed(
        self,
        tool: str,
        args: Dict = None,
        result_summary: str = "",
        success: bool = True,
    ):
        """Notify SkillCell that a tool was used."""
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        self._skill.receive(Signal(
            source="luo_memory",
            target="skill",
            signal_type="tool_executed",
            payload={
                "tool": tool,
                "args": args or {},
                "result_summary": result_summary,
                "success": success,
            },
        ))

    async def task_completed(self, goal: str = "", success: bool = True):
        """
        Signal that a task is done. SkillCell will consider crystallizing
        the tool chain into a reusable skill.
        """
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        self._skill.receive(Signal(
            source="luo_memory",
            target="skill",
            signal_type="task_completed",
            payload={"goal": goal, "success": success},
        ))

    async def list_skills(self) -> List[Dict]:
        """Return all crystallized skills."""
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        payload: Dict = {}
        self._skill.receive(Signal(
            source="luo_memory",
            target="skill",
            signal_type="list_skills",
            payload=payload,
        ))
        await asyncio.sleep(0.15)
        return payload.get("_results", [])

    # ── dream / consolidation ──────────────────────────────────────────

    async def dream(self):
        """Manually trigger dream consolidation (normally runs on idle)."""
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        self._dream.receive(Signal(
            source="luo_memory",
            target="dream",
            signal_type="force_dream",
            payload={},
        ))
        await asyncio.sleep(0.5)
        logger.info("[luo_memory] dream consolidation triggered")

    # ── goal management ────────────────────────────────────────────────

    async def set_goal(self, description: str, priority: int = 5,
                       deadline: str = None):
        """Set a persistent goal that survives across sessions."""
        if not self._started:
            await self.start()
        Signal = __import__('luo_cell').Signal
        self._goal.receive(Signal(
            source="luo_memory", target="goal",
            signal_type="set_goal",
            payload={"description": description,
                     "priority": priority, "deadline": deadline},
        ))

    async def get_goals(self) -> List[Dict]:
        """Return all active goals."""
        if not self._started:
            await self.start()
        Signal = __import__('luo_cell').Signal
        payload: Dict = {}
        self._goal.receive(Signal(
            source="luo_memory", target="goal",
            signal_type="get_goals", payload=payload,
        ))
        await asyncio.sleep(0.15)
        return payload.get("_active", [])

    # ── temporal queries ───────────────────────────────────────────────

    async def query_time(self, period: str = "today") -> List[Dict]:
        """Query timeline for a period: 'today', 'yesterday', 'this_week'."""
        if not self._started:
            await self.start()
        Signal = __import__('luo_cell').Signal
        payload: Dict = {"period": period}
        self._temporal.receive(Signal(
            source="luo_memory", target="temporal",
            signal_type="query_time", payload=payload,
        ))
        await asyncio.sleep(0.15)
        return payload.get("_results", [])

    # ── confidence / metacognition ─────────────────────────────────────

    async def confidence(self, query: str) -> float:
        """
        Returns 0.0–1.0 confidence that luo_memory has knowledge
        relevant to this query. Low score = agent should caveat its answer.
        """
        if not self._started:
            await self.start()
        Signal = __import__('luo_cell').Signal
        payload: Dict = {"query": query}
        self._meta.receive(Signal(
            source="luo_memory", target="meta",
            signal_type="confidence_check", payload=payload,
        ))
        await asyncio.sleep(0.1)
        return payload.get("_confidence", 0.0)

    # ── raw input via sensory filter ──────────────────────────────────

    async def sense(self, content: str, channel: str = "chat"):
        """
        Send raw input through SensoryCell before storage.
        SensoryCell deduplicates, filters noise, and routes to the
        right cells automatically. Prefer this over store() for
        high-frequency inputs like tool results.
        """
        if not self._started:
            await self.start()
        Signal = __import__('luo_cell').Signal
        self._sensory.receive(Signal(
            source="luo_memory", target="sensory",
            signal_type="raw_input",
            payload={"content": content, "channel": channel,
                     "session_id": self._session_id},
        ))

    async def spread(self, concept: str) -> List[Dict]:
        """Return concepts associated with a given concept (spreading activation)."""
        if not self._started:
            await self.start()

        Signal = __import__('luo_cell').Signal
        payload: Dict = {"concept": concept}
        self._associative.receive(Signal(
            source="luo_memory",
            target="associative",
            signal_type="activate",
            payload=payload,
        ))
        await asyncio.sleep(0.15)
        return payload.get("_neighbors", [])

    # ── network introspection ──────────────────────────────────────────

    def status(self) -> Dict:
        """Return the current status of all cells."""
        return {
            "version": self.VERSION,
            "palace_path": self.palace_path,
            "session_id": self._session_id,
            "started": self._started,
            "network": self.network.status(),
        }

    def __repr__(self):
        return (
            f"<LuoMemory v{self.VERSION} "
            f"cells={len(self.network._cells)} "
            f"path={self.palace_path}>"
        )


# ── convenience: synchronous wrapper for non-async contexts ───────────

class LuoMemorySync:
    """
    Synchronous wrapper around LuoMemory for use in non-async code.
    Creates its own event loop if one doesn't exist.
    """

    def __init__(self, palace_path: Optional[str] = None):
        self._mem = LuoMemory(palace_path)
        self._loop = asyncio.new_event_loop()

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    def start(self):            return self._run(self._mem.start())
    def stop(self):             return self._run(self._mem.stop())
    def store(self, *a, **kw):  return self._run(self._mem.store(*a, **kw))
    def recall(self, *a, **kw): return self._run(self._mem.recall(*a, **kw))
    def wake_up(self, *a, **kw):return self._run(self._mem.wake_up(*a, **kw))
    def get_facts(self):        return self._run(self._mem.get_facts())
    def dream(self):            return self._run(self._mem.dream())
    def list_skills(self):      return self._run(self._mem.list_skills())
    def status(self):           return self._mem.status()
    def set_goal(self, *a, **kw):  return self._run(self._mem.set_goal(*a, **kw))
    def get_goals(self):           return self._run(self._mem.get_goals())
    def query_time(self, *a, **kw):return self._run(self._mem.query_time(*a, **kw))
    def confidence(self, query):   return self._run(self._mem.confidence(query))
    def sense(self, *a, **kw):     return self._run(self._mem.sense(*a, **kw))
    def spread(self, concept):     return self._run(self._mem.spread(concept))

    def task_completed(self, goal="", success=True):
        return self._run(self._mem.task_completed(goal, success))

    def tool_executed(self, tool, args=None, result_summary="", success=True):
        return self._run(
            self._mem.tool_executed(tool, args, result_summary, success)
        )


# ── CLI ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    mem = LuoMemorySync()
    mem.start()

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        import json
        print(json.dumps(mem.status(), indent=2))

    elif cmd == "wake":
        print(mem.wake_up())

    elif cmd == "store":
        content = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if content:
            mem.store(content)
            print(f"stored: {content[:60]}...")
        else:
            print("usage: luo_memory.py store <text>")

    elif cmd == "recall":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = mem.recall(query=query)
        for r in results:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["timestamp"]))
            print(f"[{ts}] {r['content'][:100]}")

    elif cmd == "facts":
        for f in mem.get_facts():
            print(f"  {f['key']}: {f['value'][:80]} (confidence={f['confidence']:.2f})")

    elif cmd == "skills":
        for s in mem.list_skills():
            print(f"  {s['name']}: {s['description'][:60]} (used {s['success_count']}x)")

    elif cmd == "dream":
        mem.dream()
        print("dream consolidation complete")

    else:
        print("commands: status | wake | store <text> | recall [query] | facts | skills | dream")

    mem.stop()
