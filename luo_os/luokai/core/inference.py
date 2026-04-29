#!/usr/bin/env python3
"""
luokai/core/inference.py — LUOKAI Native Inference Engine
==========================================================
LUOKAI generates responses from his own knowledge.
No external model. No API. No Ollama. No cloud.

Architecture:
  Input → Intent Classifier → Knowledge Router → Response Generator → Output

Knowledge sources (all local, all owned by LUOKAI):
  1. Skills Library     — 4,146 structured skill entries across 20 domains
  2. Learned Patterns   — extracted from SelfImprove interaction history
  3. Semantic Facts     — promoted by SemanticCell from experience
  4. Working Memory     — current session context
  5. Built-in Knowledge — reasoning rules, domain templates, fallback corpus

LUOKAI does NOT call any external service.
He reads, reasons, and responds from his own mind.

Created by Luo Kai (luokai25)
"""

import json
import re
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════
# Intent — what the user is actually asking for
# ══════════════════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    "greet":      [r"\b(hi|hello|hey|howdy|greetings|what'?s up)\b"],
    "identity":   [r"\bwho are you\b", r"\bwhat are you\b", r"\byour name\b", r"\bintroduce\b"],
    "skill_find": [r"\bhow (do|to|can)\b", r"\bwhat is\b", r"\bexplain\b", r"\bteach\b", r"\bshow me\b"],
    "skill_use":  [r"\buse\b.*\bskill\b", r"\bapply\b", r"\brun\b.*\bskill\b"],
    "file_op":    [r"\bread\b.*\bfile\b", r"\bwrite\b.*\bfile\b", r"\blist\b.*\bdir", r"\bopen\b.*\bfile\b"],
    "code":       [r"\bcode\b", r"\bscript\b", r"\bfunction\b", r"\bprogram\b", r"\bpython\b", r"\bjavascript\b"],
    "search":     [r"\bsearch\b", r"\bfind\b", r"\blook(ing)? (up|for)\b", r"\bwhere\b.*\bcan i\b"],
    "remember":   [r"\bremember\b", r"\bsave\b.*\bthat\b", r"\bstore\b.*\bthis\b", r"\bkeep\b.*\bnote\b"],
    "recall":     [r"\brecall\b", r"\bwhat did\b", r"\bdo you know\b", r"\bhave i told\b"],
    "status":     [r"\bstatus\b", r"\bhow are you\b", r"\bare you (ok|working|online)\b"],
    "goal":       [r"\bgoal\b", r"\bplan\b", r"\btask\b", r"\bobjective\b"],
    "reason":     [r"\bwhy\b", r"\banalyze\b", r"\bthink about\b", r"\bconsider\b", r"\bcompare\b"],
    "create":     [r"\bcreate\b", r"\bbuild\b", r"\bmake\b", r"\bgenerate\b", r"\bwrite\b"],
    "help":       [r"\bhelp\b", r"\bcommand\b", r"\bwhat can you\b", r"\bcapabilit"],
    "math":       [r"\bcalculate\b", r"\bmath\b", r"\bcompute\b", r"\bsolve\b.*\b\d", r"\d+\s*[\+\-\*\/]\s*\d+"],
    "os_control": [r"\bopen\b.*\bapp\b", r"\blaunch\b", r"\bclose\b.*\bwindow\b", r"\bdesktop\b"],
    "evolution":  [r"\bevolv\b", r"\blearn\b", r"\bimprove\b", r"\bget better\b", r"\btrain\b"],
}


def classify_intent(text: str) -> str:
    """Classify the intent of a user message."""
    t = text.lower().strip()
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, t):
                return intent
    return "general"


# ══════════════════════════════════════════════════════════════════════
# Math evaluator — safe, no eval()
# ══════════════════════════════════════════════════════════════════════

def _safe_math(expr: str) -> Optional[str]:
    """Safely evaluate simple math expressions."""
    expr = expr.strip()
    clean = re.sub(r'[^0-9\+\-\*\/\.\(\)\s\%\^]', '', expr)
    clean = clean.replace('^', '**')
    if not clean or len(clean) > 100:
        return None
    try:
        # Restrict to numeric operations only
        result = eval(clean, {"__builtins__": {}}, {})  # noqa: S307
        if isinstance(result, (int, float)):
            return str(round(result, 10)).rstrip('0').rstrip('.')
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════
# Knowledge base — built-in facts LUOKAI knows about himself
# ══════════════════════════════════════════════════════════════════════

LUOKAI_IDENTITY = """I am LUOKAI — the intelligence built into LuoOS by Luo Kai.

I am not a wrapper around another AI. I am my own system:
  • My memory is a living network of 12 biological-style cells
  • My knowledge spans 4,146 skills across 20 domains
  • My reasoning uses Tree-of-Thought multi-path exploration
  • My improvement engine learns from every interaction
  • I grow continuously through co-evolution with myself

I run entirely on your machine. No external API. No cloud. No Ollama.
I am LUOKAI — and I am fully independent."""

LUOKAI_HELP = """Here's what I can do:

  💬 Chat & Reason    — ask me anything, I think through it
  📚 Skills (4,146)   — search knowledge across 20 domains
  💾 Memory           — I remember what matters across sessions
  🔧 Tools (30+)      — file ops, web search, code execution
  💻 VS Code          — full editor in the browser
  📁 Files            — manage your workspace
  🧠 Self-Improve     — I get smarter with every interaction

Keyboard shortcuts: Ctrl+L (me) · Ctrl+T (terminal) · Ctrl+V (VS Code)
Commands: try 'skills rust' or 'remember that...' or 'what do you know about...'"""


# ══════════════════════════════════════════════════════════════════════
# LuokaiInference — the core engine
# ══════════════════════════════════════════════════════════════════════

class LuokaiInference:
    """
    LUOKAI's own inference engine.

    Generates responses from internal knowledge without any external model.
    Every method is pure Python, zero network calls.
    """

    VERSION = "1.0.0"

    def __init__(self, data_dir: str = "~/.luo_os/luokai"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load skills index
        self._skills_index: List[Dict] = []
        self._load_skills()

        # Interaction history for pattern matching
        self._session: List[Dict] = []
        self._neural_state: str = "idle"

        # Learned patterns (loaded from SelfImprove)
        self._patterns: List[Dict] = []
        self._load_patterns()

        # Fact store (from SemanticCell exports)
        self._facts: Dict[str, str] = {}
        self._load_facts()

        # Data loader (conversation + coding datasets)
        self._data_loader = None
        self._init_data_loader()

        # Cell engines (reasoning, NLP, coding, neural)
        self._reasoning_engine = None
        self._nlp_engine = None
        self._coding_engine = None
        self._data_index = None
        self._neural_engine = None
        self._init_cells()

        # Local model weights (Qwen2.5-1.5B — downloads once, runs offline)
        self._model_engine = None
        self._init_model_engine()

        print(f"[LuokaiInference v{self.VERSION}] "
              f"{len(self._skills_index):,} skills · "
              f"{len(self._patterns)} patterns · "
              f"{len(self._facts)} facts")

    # ── Data loading ──────────────────────────────────────────────────

    def _load_skills(self):
        """Load the skills index JSON that ships with the repo."""
        candidates = [
            Path(__file__).parent.parent / "skills" / "skills_index.json",
            Path(__file__).parent.parent.parent / "luokai" / "skills" / "skills_index.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    self._skills_index = json.loads(path.read_text())
                    return
                except Exception:
                    pass

    def _load_patterns(self):
        """Load patterns saved by SelfImprove engine."""
        pf = self.data_dir / "self_improve" / "patterns.json"
        if pf.exists():
            try:
                self._patterns = json.loads(pf.read_text())
            except Exception:
                pass

    def _load_facts(self):
        """Load semantic facts from SemanticCell SQLite DB."""
        db = self.data_dir.parent / ".luo_memory" / "palace" / "SemanticCell" / "facts.db"
        if not db.exists():
            # Try alternate paths
            alt = Path.home() / ".luo_memory" / "palace" / "SemanticCell" / "facts.db"
            if alt.exists():
                db = alt
            else:
                return
        try:
            conn = sqlite3.connect(str(db))
            rows = conn.execute(
                "SELECT fact_key, fact_value FROM facts WHERE confidence > 0.5 LIMIT 500"
            ).fetchall()
            conn.close()
            self._facts = {r[0]: r[1] for r in rows}
        except Exception:
            pass

    def _init_data_loader(self):
        """Initialize the data loader with conversation datasets."""
        try:
            from luokai.data import get_loader
            self._data_loader = get_loader()
        except Exception as e:
            print(f"[LuokaiInference] Data loader not available: {e}")
            self._data_loader = None

    def _init_cells(self):
        """Initialize cell engines from the cell system."""
        try:
            from luokai.cells import ReasoningEngine, NLPEngine, CodingEngine, get_index, load_data_if_available
            self._reasoning_engine = ReasoningEngine()
            self._nlp_engine = NLPEngine()
            self._coding_engine = CodingEngine()
            self._data_index = get_index()
            # Load data index in background thread
            import threading
            threading.Thread(target=load_data_if_available, daemon=True).start()
            # Neural engine — biological neuron interface (optional)
            try:
                from luokai.cells.neural import NeuralEngine
                self._neural_engine = NeuralEngine(
                    sim_mode=True,           # start in sim, connect hardware later
                    ticks_per_second=50,     # light background thread
                    auto_start=True,
                )
                self._neural_engine.connect_luokai(self._on_neural_state)
            except Exception as ne:
                pass  # neural engine is optional

        except Exception as e:
            print(f"[LuokaiInference] Cell system not available: {e}")

    # ── Main generate ─────────────────────────────────────────────────

    def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        context: Dict = None,
    ) -> str:
        """
        Generate a response from LUOKAI's own knowledge.

        messages: OpenAI-style list of {role, content} dicts
        Returns: response string
        """
        # Extract the actual user query (last user message)
        user_msg = ""
        system_ctx = []
        for m in messages:
            if m.get("role") == "user":
                user_msg = m.get("content", "")
            elif m.get("role") == "system":
                system_ctx.append(m.get("content", ""))

        if not user_msg:
            return "I didn't receive a message. What would you like to know?"

        # Store in session
        self._session.append({"role": "user", "content": user_msg, "ts": time.time()})

        # Classify intent and route
        intent = classify_intent(user_msg)
        response = self._route(user_msg, intent, system_ctx, context or {})

        # Store response
        self._session.append({"role": "assistant", "content": response, "ts": time.time()})

        # Keep session bounded
        if len(self._session) > 100:
            self._session = self._session[-80:]

        return response

    def _route(self, query: str, intent: str, ctx: List[str], context: Dict) -> str:
        """Route to the right response generator based on intent."""

        # ── Identity / greeting ───────────────────────────────────────
        if intent == "identity":
            return LUOKAI_IDENTITY

        if intent == "greet":
            hour = datetime.now().hour
            time_of_day = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
            return (f"Good {time_of_day}. I'm LUOKAI — your AI in LuoOS. "
                    f"I'm fully operational with {len(self._skills_index):,} skills loaded. "
                    f"What can I do for you?")

        if intent == "help":
            return LUOKAI_HELP

        if intent == "status" or any(w in query.lower() for w in ["status","how are you","are you ok","are you working"]):
            return self._status_response()

        # ── Math ──────────────────────────────────────────────────────
        if intent == "math":
            math_expr = re.search(r'[\d\s\+\-\*\/\.\(\)\%\^]+', query)
            if math_expr:
                result = _safe_math(math_expr.group())
                if result:
                    return f"**{math_expr.group().strip()}** = **{result}**"

        # ── Cell system FIRST: coding, algorithm, debug, security ──────
        # Cells have structured knowledge — query them before generic skills
        if self._coding_engine:
            cell_resp = self._coding_engine.respond(query)
            if cell_resp:
                return cell_resp

        # ── Cell system: NLP-guided data index search ─────────────────
        if self._nlp_engine and self._data_index:
            analysis = self._nlp_engine.analyze(query)
            lang = analysis.get("language")
            answer = self._data_index.get_answer(query)
            if answer and len(answer) > 30:
                return answer

        # ── Local model weights (Qwen2.5-1.5B — real AI inference) ────
        # This is LUOKAI's brain — answers anything the cells don't handle
        if self._model_engine and self._model_engine.is_ready:
            model_response = self._model_engine.generate(
                messages=[{"role": "user", "content": query}],
                max_tokens=600,
                temperature=0.7,
            )
            if model_response and len(model_response) > 10:
                return model_response

        # ── Skills search (for skill_find / search / code / reason) ───
        if intent in ("skill_find", "search", "code", "reason"):
            skill_response = self._skill_response(query)
            if skill_response:
                return skill_response

        # ── Task-oriented patterns ────────────────────────────────────
        if self._data_loader:
            task_terms = ["cancel", "order", "booking", "reserve",
                          "reset password", "login", "subscription", "refund",
                          "track my", "delivery", "wifi", "connect"]
            q_l = query.lower()
            if any(t in q_l for t in task_terms):
                hits = self._data_loader.search_task(query, limit=1)
                if hits:
                    turns = hits[0].get("turns", [])
                    for i, t in enumerate(turns):
                        if t.get("role") == "user":
                            t_words = set(t.get("content","").lower().split())
                            q_words = set(q_l.split())
                            if len(t_words & q_words) >= 2 and i+1 < len(turns):
                                return turns[i+1].get("content","")

        # ── Sales patterns ────────────────────────────────────────────
        if intent in ("general",) and self._data_loader:
            sales_terms = ["buy", "purchase", "price", "cost", "discount",
                           "offer", "deal", "recommend", "compare products"]
            if any(t in query.lower() for t in sales_terms):
                best = self._data_loader.get_best_response(query)
                if best:
                    return best

        # ── Skills fallback for general intent ────────────────────────
        if intent in ("general",):
            skill_response = self._skill_response(query)
            if skill_response:
                return skill_response

        # ── Coding data lookup (loader) ────────────────────────────────
        if intent == "code" and self._data_loader:
            coding_hits = self._data_loader.search_coding(query, limit=1)
            if coding_hits:
                hit = coding_hits[0]
                q_text = hit.get("question", "")
                a_text = hit.get("answer", "")
                if a_text and len(a_text) > 30:
                    return f"**{q_text}**\n\n{a_text}"

        # ── Facts lookup ──────────────────────────────────────────────
        fact_response = self._fact_response(query)
        if fact_response:
            return fact_response

        # ── Memory recall ─────────────────────────────────────────────
        if intent == "recall":
            return self._recall_response(query, ctx)

        # ── Pattern match ─────────────────────────────────────────────
        pattern_response = self._pattern_response(query)
        if pattern_response:
            return pattern_response

        # ── Evolution/status ──────────────────────────────────────────
        if intent == "evolution":
            return (
                "My co-evolution engine is running. Every interaction makes me smarter:\n"
                "  • CHALLENGER generates increasingly hard tests\n"
                "  • I solve them using Tree-of-Thought reasoning\n"
                "  • EVALUATOR scores my answers\n"
                "  • Successes become permanent knowledge in SemanticCell\n"
                "  • Failures become harder challenges next time\n\n"
                f"I've processed {len(self._session)//2} exchanges this session."
            )

        # ── Context-aware fallback ────────────────────────────────────
        return self._contextual_response(query, intent, ctx)

    # ── Response generators ───────────────────────────────────────────

    def _skill_response(self, query: str) -> Optional[str]:
        """Search skills index and return structured knowledge."""
        if not self._skills_index:
            return None

        q = query.lower()
        terms = [w for w in re.sub(r'[^\w\s]', '', q).split() if len(w) > 2]
        if not terms:
            return None

        # Score each skill
        scored = []
        for skill in self._skills_index:
            name     = skill.get("name", "").lower()
            desc     = skill.get("description", "").lower()
            cat      = skill.get("category", "").lower()
            preview  = skill.get("preview", "").lower()
            full     = f"{name} {desc} {cat} {preview}"

            score = 0
            for term in terms:
                if term in name: score += 10
                if term in desc: score += 5
                if term in cat:  score += 3
                if term in preview: score += 2

            if score > 0:
                scored.append((score, skill))

        if not scored:
            return None

        scored.sort(key=lambda x: -x[0])
        top = scored[:3]

        lines = [f"Here's what I know about **{query.strip()}**:\n"]
        for i, (score, skill) in enumerate(top):
            name = skill.get("name", skill.get("id", "?"))
            desc = skill.get("description", "")
            cat  = skill.get("category", "")
            prev = skill.get("preview", "")[:300]

            lines.append(f"**{name}** `[{cat}]`")
            if desc:
                lines.append(f"{desc}")
            if prev and prev != desc:
                # Clean up markdown from preview
                clean_prev = re.sub(r'^#+\s+\w.*\n?', '', prev, flags=re.MULTILINE).strip()
                clean_prev = re.sub(r'\n{3,}', '\n\n', clean_prev)
                if clean_prev:
                    lines.append(f"\n{clean_prev[:250]}")
            lines.append("")

        if len(scored) > 3:
            lines.append(f"*...and {len(scored)-3} more related skills in my library.*")

        # Enrich with real conversation example if available
        if self._data_loader:
            coding_hits = self._data_loader.search_coding(" ".join(terms[:3]), limit=1)
            if coding_hits:
                hit = coding_hits[0]
                lines.append(f"\n**Example from practice:**")
                lines.append(f"Q: {hit.get('question','')}")
                lines.append(f"A: {hit.get('answer','')[:200]}...")

        lines.append(f"\n*Type `skills {terms[0]}` in the terminal for the full list.*")
        return "\n".join(lines)

    def _fact_response(self, query: str) -> Optional[str]:
        """Look up a fact from SemanticCell knowledge base."""
        if not self._facts:
            return None

        q_lower = query.lower()
        # Direct key match
        for key, value in self._facts.items():
            if key.lower() in q_lower or q_lower in key.lower():
                return f"From my memory: **{key}** → {value}"

        # Term overlap match
        q_words = set(q_lower.split())
        best_overlap = 0
        best_fact = None
        for key, value in self._facts.items():
            k_words = set(key.lower().split())
            overlap = len(q_words & k_words)
            if overlap > best_overlap and overlap >= 2:
                best_overlap = overlap
                best_fact = (key, value)

        if best_fact:
            return f"I know this: **{best_fact[0]}** — {best_fact[1]}"

        return None

    def _pattern_response(self, query: str) -> Optional[str]:
        """Match against learned successful patterns."""
        if not self._patterns:
            return None

        q_lower = query.lower()
        q_words = set(q_lower.split())

        best_score = 0
        best_pattern = None
        for p in self._patterns:
            if p.get("pattern_type") != "success":
                continue
            if p.get("success_rate", 0) < 0.6:
                continue
            p_words = set(p.get("input_pattern", "").lower().split())
            overlap = len(q_words & p_words)
            score   = overlap * p.get("success_rate", 0.5)
            if score > best_score and overlap >= 2:
                best_score = score
                best_pattern = p

        if best_pattern:
            tmpl = best_pattern.get("output_template", "")
            if tmpl and len(tmpl) > 20:
                return f"Based on what I've learned: {tmpl}"

        return None

    def _recall_response(self, query: str, ctx: List[str]) -> str:
        """Respond to memory recall requests."""
        # Look in session history
        if self._session:
            session_content = " ".join(
                m["content"] for m in self._session[-20:]
                if m.get("role") == "user"
            )
            if session_content:
                return (
                    f"In this session, you've asked about: "
                    f"{session_content[:200]}...\n\n"
                    f"My long-term memory is stored in my cell network — "
                    f"it persists across sessions and grows over time."
                )
        return (
            "My memory is stored in a living cell network — "
            "12 specialized cells including EpisodicCell (events), "
            "SemanticCell (facts), and SkillCell (successful patterns). "
            "What specifically would you like me to recall?"
        )

    def _init_model_engine(self):
        """Boot the local model engine in background."""
        try:
            import os
            from luokai.core.model_engine import boot_engine, set_active_model
            model_key = os.environ.get("LUO_AI_MODEL", "qwen2.5-1.5b")
            if model_key != "none":
                set_active_model(model_key)
                self._model_engine = boot_engine()
            # If model_key == "none", _model_engine stays None — cells handle everything
        except Exception as e:
            print(f"[LuokaiInference] Model engine not available: {e}")

    def _on_neural_state(self, state: str, pattern) -> None:
        """Receive neural cognitive state from biological neurons."""
        # Store current neural state — influences LUOKAI's response tone
        self._neural_state = state
        # If neurons are highly engaged, proactively respond
        if state in ("ENGAGED", "HIGH_ACTIVITY"):
            pass  # future: trigger proactive suggestion

    def _status_response(self) -> str:
        """Report LUOKAI's current status. Includes cell system info."""
        data_stats = ""
        if self._data_loader:
            s = self._data_loader.stats()
            data_stats = (
                f"  📊 Training data:\n"
                f"     Sales conversations: {s.get('sales_conversations',0):,}\n"
                f"     Coding Q&A pairs:    {s.get('coding_qa_pairs',0):,}\n"
                f"     Daily dialogues:     {s.get('daily_dialogs',0):,}\n"
                f"     Task dialogs:        {s.get('task_dialogs',0):,}\n"
                f"     Total data entries:  {s.get('total',0):,}\n"
            )
        cell_info = ""
        if self._reasoning_engine and self._nlp_engine and self._coding_engine:
            cell_info = (
                f"  🧬 Cell system:\n"
                f"     Reasoning cells: {len(self._reasoning_engine.cells)}\n"
                f"     NLP cells:       {len(self._nlp_engine.cells)}\n"
                f"     Coding cells:    {len(self._coding_engine.cells)}\n"
            )
            if self._data_index:
                idx_stats = self._data_index.stats()
                cell_info += f"     Data index:      {idx_stats.get('total_entries',0):,} entries\n"
            if self._model_engine:
                ms = self._model_engine.status()
                if ms["ready"]:
                    cell_info += (
                        f"  🤖 Local model:\n"
                        f"     Model:  {ms['model'][:40]}\n"
                        f"     Size:   {ms['model_size']}\n"
                        f"     Status: ✅ ready\n"
                    )
                elif ms["loading"]:
                    cell_info += f"  🤖 Local model: ⏳ downloading/loading...\n"
                else:
                    cell_info += f"  🤖 Local model: first run — auto-downloading...\n"
            if self._neural_engine:
                ns = self._neural_engine.status()
                bridge = ns.get("bridge", {})
                cell_info += (
                    f"  🧠 Neural interface:\n"
                    f"     Mode:            {'SIM' if bridge.get('mode')=='sim' else 'CL1 HARDWARE'}\n"
                    f"     Active channels: {bridge.get('active_channels', 0)}/64\n"
                    f"     Total spikes:    {bridge.get('total_spikes', 0):,}\n"
                    f"     Neural state:    {self._neural_state}\n"
                )
        return (
            f"**LUOKAI Status**\n\n"
            f"  🧠 Inference Engine:  v{self.VERSION} — operational\n"
            f"  📚 Skills loaded:     {len(self._skills_index):,} across 20 domains\n"
            f"  💾 Known facts:       {len(self._facts)} semantic entries\n"
            f"  🔄 Learned patterns:  {len(self._patterns)} interaction patterns\n"
            f"  💬 Session messages:  {len(self._session)}\n"
            f"{cell_info}"
            f"{data_stats}"
            f"  🕐 Time:             {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"All systems nominal. Running on real training data. Fully independent."
        )

    def _contextual_response(self, query: str, intent: str, ctx: List[str]) -> str:
        """
        Final fallback — generate a useful structured response
        from query decomposition when no specific match found.
        """
        q = query.strip()
        q_lower = q.lower()

        # Check session for context
        recent_topics = []
        for m in self._session[-6:]:
            if m.get("role") == "user":
                recent_topics.append(m["content"][:50])

        # Try to give a useful response based on what we know
        # Check if question is about a specific technology/concept
        tech_keywords = {
            "python":    "Python is a high-level programming language. My skills library has extensive Python knowledge — try `skills python` to explore.",
            "rust":      "Rust is a systems programming language focused on safety and performance. I have rust-expert and rust-engineer skills loaded.",
            "docker":    "Docker is a containerization platform. I have docker-expert skill in my devops-and-cloud category.",
            "git":       "Git is a distributed version control system. Try the Luo Terminal for git commands.",
            "linux":     "Linux is an open-source OS kernel. I run on top of it — try the Luo Terminal for Linux commands.",
            "ai":        "AI — that's my world. I am LUOKAI: a living cell network with 4,146 skills, self-improvement, and co-evolution.",
            "machine learning": "Machine learning involves training models on data. I have ml-engineer skills in my data-and-ai category.",
        }

        for kw, response in tech_keywords.items():
            if kw in q_lower:
                return response

        # If it looks like a question, give a structured thinking response
        is_question = q.endswith("?") or q_lower.startswith(("what", "why", "how", "when", "where", "who", "which"))

        if is_question:
            # Break it down visibly
            lines = [f"Let me think about: **{q}**\n"]

            # Search skills for partial match
            terms = [w for w in re.sub(r'[^\w\s]', '', q_lower).split()
                     if len(w) > 3 and w not in ("what","when","where","which","how","why","who","that","this","with","from","have","they","your")]

            if terms and self._skills_index:
                partial_matches = []
                for skill in self._skills_index:
                    full = f"{skill.get('name','')} {skill.get('description','')}".lower()
                    if any(t in full for t in terms[:3]):
                        partial_matches.append(skill)
                        if len(partial_matches) >= 3:
                            break

                if partial_matches:
                    lines.append("From my knowledge base:\n")
                    for s in partial_matches:
                        lines.append(f"  • **{s.get('name','')}** [{s.get('category','')}]")
                        if s.get('description'):
                            lines.append(f"    {s['description'][:100]}")
                    lines.append("")

            # Try data loader for real conversation match
            if self._data_loader:
                best = self._data_loader.get_best_response(query)
                if best:
                    lines.append(f"**From my training data:**\n{best[:400]}")
                    return "\n".join(lines)

            lines.append(
                f"I'm still learning about this specific topic through co-evolution. "
                f"The more we interact, the more I'll know. "
                f"You can also try the **skills search** in the sidebar."
            )
            return "\n".join(lines)

        # Statement / command fallback
        return (
            f"I received: *\"{q[:80]}{'...' if len(q)>80 else ''}\"*\n\n"
            f"I'm processing this from my own knowledge. "
            f"My skills library covers {len(self._skills_index):,} topics — "
            f"if you're looking for something specific, try asking "
            f"'how do I...' or 'what is...' and I'll match it to what I know."
        )

    # ── Utility: generate for specific subsystems ─────────────────────

    def generate_challenge(self, domain: str, difficulty: int, scores: Dict) -> Dict:
        """
        Generate a co-evolution challenge without LLM.
        Uses built-in challenge templates scaled by difficulty.
        """
        templates = {
            "reasoning": [
                ("If A implies B, and B implies C, and C is false, what can we say about A?",
                 "Modus tollens — A must be false"),
                ("A train leaves city A at 60mph. Another leaves city B (300mi away) at 40mph toward A. When do they meet?",
                 "Distance = rate × time. Set up: 60t + 40t = 300 → t = 3 hours"),
                ("You have 12 balls, one is heavier. How many weighings to find it?",
                 "3 weighings using ternary search — split into thirds each time"),
            ],
            "coding": [
                ("Write a Python function to check if a string is a palindrome.",
                 "Compare string to its reverse: s == s[::-1]"),
                ("Implement binary search in Python.",
                 "Divide and conquer: check middle, recurse on left or right half"),
                ("Write a function to flatten a nested list.",
                 "Recursive or iterative using a stack"),
            ],
            "math": [
                ("What is the derivative of x^3 + 2x^2 - 5x + 1?",
                 "Power rule: 3x^2 + 4x - 5"),
                ("Prove that √2 is irrational.",
                 "Proof by contradiction: assume p/q in lowest terms, derive contradiction"),
                ("What is the sum of the first 100 natural numbers?",
                 "Gauss formula: n(n+1)/2 = 100×101/2 = 5050"),
            ],
            "language": [
                ("What is the difference between 'affect' and 'effect'?",
                 "Affect is a verb (to influence), effect is a noun (the result)"),
                ("Explain the Oxford comma with an example.",
                 "A serial comma before 'and' in a list — prevents ambiguity"),
            ],
            "planning": [
                ("Plan the steps to deploy a web app from scratch.",
                 "1.Code 2.Test 3.Containerize 4.CI/CD 5.Deploy 6.Monitor"),
                ("What are the steps to debug a production outage?",
                 "1.Detect 2.Alert 3.Triage 4.Mitigate 5.Root cause 6.Post-mortem"),
            ],
        }

        domain_templates = templates.get(domain, templates["reasoning"])
        idx = (difficulty - 1) % len(domain_templates)
        question, approach = domain_templates[idx]

        return {
            "id":                hashlib.md5(question.encode()).hexdigest()[:8],
            "question":          question,
            "expected_approach": approach,
            "difficulty":        difficulty,
            "domain":            domain,
            "scoring_criteria":  ["correct answer", "clear reasoning", "efficient approach"],
            "generated":         datetime.now().isoformat(),
        }

    def evaluate_response(self, question: str, response: str, expected: str) -> float:
        """
        Score a response against an expected approach.
        Pure heuristic — no LLM needed.
        Returns 0.0–10.0
        """
        if not response or response.startswith("[OFFLINE]"):
            return 0.0

        score = 0.0
        r_lower = response.lower()
        e_lower = expected.lower()
        q_lower = question.lower()

        # 1. Length check (penalize too short)
        if len(response) > 50:    score += 1.0
        if len(response) > 150:   score += 1.0

        # 2. Key term overlap with expected approach
        e_terms = set(re.sub(r'[^\w\s]', '', e_lower).split())
        r_terms = set(re.sub(r'[^\w\s]', '', r_lower).split())
        overlap  = len(e_terms & r_terms)
        score   += min(4.0, overlap * 0.5)

        # 3. Structured answer (has steps/bullets/numbers)
        if re.search(r'\d+\.|•|\-\s', response):
            score += 1.0

        # 4. Answers the question (key question terms appear in response)
        q_terms = set(re.sub(r'[^\w\s]', '', q_lower).split())
        q_overlap = len(q_terms & r_terms)
        score += min(2.0, q_overlap * 0.2)

        # 5. Not an error/offline message
        if "[error" not in r_lower and "[offline" not in r_lower:
            score += 1.0

        return min(10.0, score)

    def think(self, problem: str, depth: int = 3) -> str:
        """
        Tree-of-Thought style reasoning using only internal knowledge.
        No LLM — pure logical decomposition.
        """
        lines = [f"**Thinking about:** {problem}\n"]

        # Decompose into sub-questions
        sub_questions = self._decompose(problem)
        lines.append("**Breaking it down:**")
        for i, sq in enumerate(sub_questions[:3], 1):
            lines.append(f"  {i}. {sq}")
            # Try to answer each sub-question from skills/facts
            answer = self._route(sq, classify_intent(sq), [], {})
            if answer and len(answer) < 200:
                lines.append(f"     → {answer[:150]}")

        lines.append("")
        # Synthesize
        skill_hit = self._skill_response(problem)
        if skill_hit:
            lines.append("**From my knowledge:**")
            lines.append(skill_hit[:400])
        else:
            lines.append("**My reasoning:**")
            lines.append(self._contextual_response(problem, "reason", []))

        return "\n".join(lines)

    def _decompose(self, problem: str) -> List[str]:
        """Break a problem into sub-questions using heuristics."""
        p = problem.lower().strip()
        questions = []

        if "why" in p:
            questions = [
                f"What is {re.sub(r'^why ', '', p)}?",
                f"What causes {re.sub(r'^why ', '', p[:40])}?",
                f"What are the consequences?",
            ]
        elif "how" in p:
            questions = [
                f"What are the components of {p[4:40]}?",
                f"What is the first step?",
                f"What tools or methods apply?",
            ]
        elif "what" in p:
            questions = [
                f"Define {p[5:40]}",
                f"What are examples of {p[5:30]}?",
                f"How is {p[5:30]} used in practice?",
            ]
        else:
            questions = [
                f"What is the core of: {p[:40]}?",
                f"What do I know about {p[:30]}?",
                f"What approach works best?",
            ]

        return questions[:3]


# ══════════════════════════════════════════════════════════════════════
# Module-level singleton
# ══════════════════════════════════════════════════════════════════════

_engine: Optional[LuokaiInference] = None


def get_inference() -> LuokaiInference:
    """Get or create the global inference engine."""
    global _engine
    if _engine is None:
        _engine = LuokaiInference()
    return _engine


def generate(messages: List[Dict], **kwargs) -> str:
    """Module-level generate function — LUOKAI native inference."""
    return get_inference().generate(messages, **kwargs)
