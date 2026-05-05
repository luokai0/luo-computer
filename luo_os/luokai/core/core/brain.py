#!/usr/bin/env python3
"""
luokai/core/brain.py — The LUOKAI Brain Bridge
================================================
Wires together every system that already exists in the repo:

  ┌─────────────────────────────────────────────────────┐
  │                  LUOKAI Brain                       │
  │                                                     │
  │  LuoMemory (luo_cell network, 12 living cells)      │
  │    ↕  sense / store / recall / wake_up              │
  │  ReActAgent (reasoning + tool execution)            │
  │    ↕  think() hooks                                 │
  │  CoEvoEngine (self-improvement loop)                │
  │    ↕  on_cycle callback → SemanticCell              │
  │  KAIROS (proactive background watcher)              │
  │    ↕  alerts → injected as system context           │
  │  TreeOfThought (multi-path reasoning)               │
  │    ↕  called for hard problems                      │
  │  SelfImprove (pattern learning)                     │
  │    ↕  records every interaction                     │
  └─────────────────────────────────────────────────────┘

Nothing here is a new concept — every system was already written.
This file makes them talk to each other.

Created by Luo Kai (luokai25) — brain wiring by Claude
"""

import asyncio
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── paths ─────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent   # repo root
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "luo_agent" / "memory"))  # for luo_cell imports

# ── optional imports (each system degrades gracefully if missing) ──────

def _try(fn):
    """Run fn, return None on any error — never crash the brain."""
    try:
        return fn()
    except Exception as e:
        print(f"[brain] ⚠ {fn.__name__ if hasattr(fn,'__name__') else '?'}: {e}")
        return None


# LuoMemory — the living cell network
_luo_memory_cls = None
try:
    from luo_agent.memory.luo_memory import LuoMemorySync
    _luo_memory_cls = LuoMemorySync
except Exception as e:
    print(f"[brain] luo_memory unavailable: {e}")

# CoEvoEngine — self-improvement loop
_coevo_cls = None
try:
    from luokai.evolution.coevo import CoEvoEngine
    _coevo_cls = CoEvoEngine
except Exception as e:
    print(f"[brain] coevo unavailable: {e}")

# KAIROS — proactive watcher
_kairos_cls = None
try:
    from ai_core.kairos import KAIROS
    _kairos_cls = KAIROS
except Exception as e:
    print(f"[brain] kairos unavailable: {e}")

# TreeOfThought — multi-path reasoning
_tot_cls = None
try:
    from luokai.core.thought import TreeOfThought
    _tot_cls = TreeOfThought
except Exception as e:
    print(f"[brain] tree-of-thought unavailable: {e}")

# SelfImprove — pattern learning
_si_cls = None
try:
    from luokai.core.self_improve import SelfImprovementEngine as SelfImprover
    _si_cls = SelfImprover
except Exception as e:
    print(f"[brain] self_improve unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════
# LuokaiBrain — the wiring layer
# ═══════════════════════════════════════════════════════════════════════

class LuokaiBrain:
    """
    Orchestrates all LUOKAI subsystems.

    Usage (inside ReActAgent.__init__):
        self._brain = LuokaiBrain(agent=self)
        self._brain.boot()

    Usage (inside ReActAgent.think):
        # Before LLM call:
        extra_ctx = self._brain.pre_think(user_input)
        # After LLM responds:
        self._brain.post_think(user_input, response, tools_used, success)
    """

    VERSION = "1.0.0"

    def __init__(self, agent=None):
        self.agent      = agent          # back-reference to ReActAgent

        # subsystem handles
        self.memory:   Optional[object] = None   # LuoMemorySync
        self.coevo:    Optional[object] = None   # CoEvoEngine
        self.kairos:   Optional[object] = None   # KAIROS
        self.tot:      Optional[object] = None   # TreeOfThought
        self.improver: Optional[object] = None   # SelfImprover

        self._booted   = False
        self._lock     = threading.RLock()
        self._session  = f"session_{int(time.time())}"

        # interaction counters
        self._interaction_count = 0
        self._coevo_interval    = 10   # run coevo every N interactions
        self._dream_interval    = 5    # trigger dream consolidation every N

    # ── boot ─────────────────────────────────────────────────────────

    def boot(self):
        """Start all subsystems. Safe to call multiple times."""
        with self._lock:
            if self._booted:
                return
            self._boot_memory()
            self._boot_coevo()
            self._boot_kairos()
            self._boot_tot()
            self._boot_improver()
            self._booted = True
            print(f"[brain] 🧠 LUOKAI Brain v{self.VERSION} online")
            self._report()

    def _boot_memory(self):
        if not _luo_memory_cls:
            return
        try:
            self.memory = _luo_memory_cls()
            self.memory.start()
            print("[brain] ✅ luo_memory: cell network alive")
        except Exception as e:
            print(f"[brain] ❌ luo_memory boot failed: {e}")
            self.memory = None

    def _boot_coevo(self):
        if not _coevo_cls:
            return
        try:
            self.coevo = _coevo_cls()
            # Register callback: every cycle result feeds into memory
            self.coevo.on_cycle(self._on_coevo_cycle)
            # Start background loop (non-blocking, every 10 min)
            threading.Thread(
                target=self.coevo.start_continuous,
                kwargs={"interval_seconds": 600},
                daemon=True, name="coevo"
            ).start()
            print("[brain] ✅ coevo: self-improvement loop running")
        except Exception as e:
            print(f"[brain] ❌ coevo boot failed: {e}")
            self.coevo = None

    def _boot_kairos(self):
        if not _kairos_cls:
            return
        try:
            self.kairos = _kairos_cls()
            threading.Thread(
                target=self.kairos.start,
                daemon=True, name="kairos"
            ).start()
            print("[brain] ✅ kairos: proactive watcher running")
        except Exception as e:
            print(f"[brain] ❌ kairos boot failed: {e}")
            self.kairos = None

    def _boot_tot(self):
        if not _tot_cls:
            return
        try:
            self.tot = _tot_cls()
            print("[brain] ✅ tree-of-thought: multi-path reasoning ready")
        except Exception as e:
            print(f"[brain] ❌ tot boot failed: {e}")
            self.tot = None

    def _boot_improver(self):
        if not _si_cls:
            return
        try:
            self.improver = _si_cls()
            print("[brain] ✅ self-improver: pattern learning active")
        except Exception as e:
            print(f"[brain] ❌ self-improver boot failed: {e}")
            self.improver = None

    # ── pre-think: inject context before LLM call ─────────────────────

    def pre_think(self, user_input: str) -> str:
        """
        Called before the LLM is invoked.
        Returns a string to prepend to the system context.
        Pulls from: luo_memory wake_up, KAIROS alerts, coevo stats.
        """
        sections = []

        # 1. Living memory context (goals, facts, recent episodes)
        if self.memory:
            try:
                ctx = self.memory.wake_up(max_tokens=600)
                if ctx and "===" in ctx:
                    sections.append(ctx)
            except Exception:
                pass

        # 2. KAIROS proactive alerts
        if self.kairos:
            try:
                alerts = self.kairos.alerts.get_unread() if hasattr(self.kairos, 'alerts') else []
                if alerts:
                    alert_lines = [f"  [{a.get('level','info').upper()}] {a.get('message','')}"
                                   for a in alerts[:3]]
                    sections.append("=== kairos alerts ===\n" + "\n".join(alert_lines))
                    self.kairos.alerts.mark_read()
            except Exception:
                pass

        # 3. Memory confidence — if low, flag it
        if self.memory:
            try:
                conf = self.memory.confidence(user_input)
                if conf < 0.2:
                    sections.append(
                        f"[metacognition] Low memory confidence ({conf:.2f}) "
                        f"for this query — be explicit about uncertainty."
                    )
            except Exception:
                pass

        # 4. Spreading activation — related concepts
        if self.memory and len(user_input.split()) >= 3:
            try:
                first_word = user_input.split()[0]
                neighbors = self.memory.spread(first_word)
                if neighbors:
                    neighbor_labels = [n.get("concept", "") for n in neighbors[:4] if n.get("concept")]
                    if neighbor_labels:
                        sections.append(
                            f"[associations] Related: {', '.join(neighbor_labels)}"
                        )
            except Exception:
                pass

        return "\n\n".join(sections)

    # ── post-think: record and learn after LLM responds ───────────────

    def post_think(
        self,
        user_input:  str,
        response:    str,
        tools_used:  List[str] = None,
        success:     bool = True,
        duration_ms: float = 0.0,
    ):
        """
        Called after the LLM responds.
        Stores the exchange, logs to self-improver, tracks skill use.
        """
        self._interaction_count += 1

        # 1. Store exchange in living memory
        if self.memory:
            try:
                # Sense through the raw-input filter (dedup + noise filter)
                self.memory.sense(f"User: {user_input}", channel="chat")
                self.memory.sense(f"LUOKAI: {response[:500]}", channel="chat")
            except Exception:
                pass

        # 2. Log tool executions to SkillCell
        if self.memory and tools_used:
            for tool in tools_used:
                try:
                    self.memory.tool_executed(
                        tool=tool,
                        result_summary=response[:200],
                        success=success,
                    )
                except Exception:
                    pass

        # 3. Signal task completion to SkillCell (may crystallize new skill)
        if self.memory and tools_used and success:
            try:
                self.memory.task_completed(goal=user_input[:100], success=success)
            except Exception:
                pass

        # 4. Record interaction in self-improver
        if self.improver:
            try:
                self.improver.record_interaction(
                    user_input=user_input,
                    response=response,
                    success=success,
                    tools_used=tools_used or [],
                    response_time=duration_ms / 1000,
                )
            except Exception:
                pass

        # 5. Periodic dream consolidation
        if self.memory and self._interaction_count % self._dream_interval == 0:
            threading.Thread(
                target=self._dream_async, daemon=True, name="dream"
            ).start()

    # ── Tree of Thought: for hard problems ───────────────────────────

    def deep_think(self, problem: str, context: str = "") -> str:
        """
        Use Tree-of-Thought multi-path reasoning for complex problems.
        Falls back to empty string if ToT unavailable.
        Called by the agent when it detects a hard problem.
        """
        if not self.tot:
            return ""
        try:
            result = self.tot.solve(
                problem=problem,
                context=context,
                max_depth=3,
                beam_width=3,
            )
            if isinstance(result, dict):
                return result.get("solution", result.get("best_path", ""))
            return str(result)
        except Exception as e:
            print(f"[brain] tot.solve error: {e}")
            return ""

    # ── CoEvo callback: feed results back into brain ──────────────────

    def _on_coevo_cycle(self, cycle_result: Dict):
        """
        Called after every co-evolution cycle.
        Feeds what was learned back into the living memory as semantic facts.
        """
        if not self.memory:
            return
        try:
            score   = cycle_result.get("score", 0)
            domain  = cycle_result.get("domain", "general")
            diff    = cycle_result.get("difficulty", 1)
            success = cycle_result.get("success", False)

            # Store result as a memory
            result_text = (
                f"[coevo] {'PASSED' if success else 'FAILED'} "
                f"{domain} challenge (difficulty {diff}, score {score:.1f})"
            )
            self.memory.sense(result_text, channel="coevo")

            # Promote successful patterns to semantic facts
            if success and score >= 7:
                solution = cycle_result.get("solution", "")
                if solution:
                    self.memory.learn_fact(
                        key=f"coevo.{domain}.strategy",
                        value=solution[:300],
                        confidence=min(0.95, score / 10),
                    )
                    print(f"[brain] coevo → memory: new {domain} strategy (score {score:.1f})")
        except Exception as e:
            print(f"[brain] coevo callback error: {e}")

    # ── helpers ───────────────────────────────────────────────────────

    def _dream_async(self):
        """Run dream consolidation in a thread."""
        if not self.memory:
            return
        try:
            self.memory.dream()
        except Exception:
            pass

    def _report(self):
        """Print what's online."""
        active = []
        if self.memory:   active.append("luo_memory")
        if self.coevo:    active.append("coevo")
        if self.kairos:   active.append("kairos")
        if self.tot:      active.append("tree-of-thought")
        if self.improver: active.append("self-improver")
        dormant = {"luo_memory", "coevo", "kairos", "tree-of-thought", "self-improver"} - set(active)
        print(f"[brain] active:  {', '.join(active) if active else 'none'}")
        if dormant:
            print(f"[brain] dormant: {', '.join(dormant)} (deps missing)")

    # ── memory passthrough API ────────────────────────────────────────
    # Let the agent call brain.store / brain.recall directly

    def store(self, content: str, role: str = "observation", importance: float = 0.5):
        if self.memory:
            try: self.memory.store(content, role=role, importance=importance)
            except Exception: pass

    def recall(self, query: str, limit: int = 8) -> List[Dict]:
        if self.memory:
            try: return self.memory.recall(query=query, limit=limit)
            except Exception: pass
        return []

    def learn_fact(self, key: str, value: str, confidence: float = 0.9):
        if self.memory:
            try: self.memory.learn_fact(key, value, confidence)
            except Exception: pass

    def set_goal(self, description: str, priority: int = 5):
        if self.memory:
            try: self.memory.set_goal(description, priority=priority)
            except Exception: pass

    def get_goals(self) -> List[Dict]:
        if self.memory:
            try: return self.memory.get_goals()
            except Exception: pass
        return []

    def get_learned_skills(self) -> List[Dict]:
        if self.memory:
            try: return self.memory.list_skills()
            except Exception: pass
        return []

    def status(self) -> Dict:
        return {
            "brain_version":  self.VERSION,
            "booted":         self._booted,
            "interactions":   self._interaction_count,
            "session":        self._session,
            "memory":         self.memory.status() if self.memory else None,
            "coevo":          self.coevo.stats() if self.coevo else None,
            "kairos":         "running" if self.kairos else None,
            "tot":            "ready"   if self.tot     else None,
            "self_improver":  "active"  if self.improver else None,
        }

    def shutdown(self):
        """Gracefully shut down all subsystems."""
        if self.coevo:
            try: self.coevo.stop()
            except Exception: pass
        if self.memory:
            try: self.memory.stop()
            except Exception: pass
        print("[brain] 🛑 LUOKAI Brain shut down")
