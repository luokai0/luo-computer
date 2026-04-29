import threading
#!/usr/bin/env python3
"""
LUOKAI Co-Evolution Engine
==========================
Your algorithm idea, fully implemented:

  LUOKAI gets better → generates harder benchmarks →
  harder benchmarks make LUOKAI better → repeat forever

Three competing systems:
  1. CHALLENGER  — generates increasingly hard tests
  2. LUOKAI      — tries to pass them, learns from failures
  3. EVALUATOR   — scores performance, decides training targets

This creates a GAN-like self-improving loop that NEVER STOPS.
The stronger LUOKAI gets, the harder CHALLENGER makes the tests.
The better the tests, the stronger LUOKAI becomes.

Components:
  - Benchmark Library: Curated challenges across domains
  - Tree-of-Thought: Multi-path reasoning for solutions
  - Adaptive Difficulty: Scales based on performance
  - Training Data Export: For fine-tuning on failures

Created by Luo Kai (luokai25) — Enhanced by Claude Code
"""
import json, time, threading, random, hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable

# Import benchmark library
try:
    from luokai.evolution.benchmarks import BenchmarkLibrary, Challenge
    BENCHMARKS_AVAILABLE = True
except ImportError:
    BENCHMARKS_AVAILABLE = False
    BenchmarkLibrary = None
    Challenge = None

class CoEvoEngine:
    """The co-evolution engine. Both AI and benchmarks improve together."""

    VERSION = "1.0"

    # Challenge domains — expand over time
    DOMAINS = [
        "reasoning", "coding", "math", "language", "planning",
        "vision_description", "tool_use", "memory_recall",
        "multi_step_logic", "creative_writing", "debate", "summarization",
    ]

    # Difficulty levels (1-10). Starts easy, gets harder as AI improves
    DIFFICULTY = {
        "reasoning":        3,
        "coding":           4,
        "math":             3,
        "language":         2,
        "planning":         3,
        "vision_description":2,
        "tool_use":         4,
        "memory_recall":    3,
        "multi_step_logic": 4,
        "creative_writing": 2,
        "debate":           3,
        "summarization":    2,
    }

    def __init__(self, data_dir: str = "~/.luo_os/coevo"):
        self.data_dir   = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.log_file    = self.data_dir / "coevo_log.jsonl"
        self.state_file  = self.data_dir / "coevo_state.json"
        self.evo_file    = self.data_dir / "evo_history.json"

        self._state      = self._load_state()
        self._running    = False
        self._lock       = threading.Lock()
        self._callbacks  : List[Callable] = []

        # Performance tracking
        self._scores     : Dict[str, List[float]] = {d: [] for d in self.DOMAINS}
        self._failures   : List[Dict]             = []

        print(f"[CoEvo] Engine v{self.VERSION} initialized")
        print(f"[CoEvo] Session #{self._state['sessions']} | Total runs: {self._state['total_runs']}")
        print(f"[CoEvo] Current AI score: {self._state['ai_score']:.1f}/10")

    def _load_state(self) -> Dict:
        default = {
            "sessions":       0,
            "total_runs":     0,
            "ai_score":       5.0,
            "challenger_level": 1,
            "domains_mastered": [],
            "current_focus":  "reasoning",
            "evolution_log":  [],
            "created":        datetime.now().isoformat(),
        }
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                pass
        return default

    def _save_state(self):
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def _call_luokai(self, prompt: str, system: str = "", model: str = "luokai", max_tokens: int = 512) -> str:
        """Generate using LUOKAI's native inference engine."""
        from luokai.core.inference import get_inference
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            return get_inference().generate(messages, max_tokens=max_tokens)
        except Exception as e:
            return f"[INFERENCE ERROR] {e}"

    # ══════════════════════════════════════════════════════
    #  CHALLENGER SYSTEM — generates test challenges
    # ══════════════════════════════════════════════════════
    def generate_challenge(self, domain: str = None, difficulty: int = None) -> Dict:
        """
        CHALLENGER generates a test.
        The harder the AI scores, the harder the next test.
        """
        domain     = domain or self._state["current_focus"]
        difficulty = difficulty or self.DIFFICULTY.get(domain, 5)
        diff_clamp = max(1, min(10, difficulty))

        # Challenger prompt — generates increasingly sophisticated tests
        challenger_system = """You are the CHALLENGER in a co-evolution system.
Your job: generate increasingly difficult test challenges for an AI called LUOKAI.
The harder LUOKAI scores, the harder YOU must make the next challenge.
Make challenges that test genuine intelligence, not just memorization.
Return ONLY valid JSON with keys: question, expected_approach, difficulty, scoring_criteria, domain"""

        challenger_prompt = f"""Generate a difficulty-{diff_clamp}/10 challenge in domain: {domain}

Current AI score in this domain: {sum(self._scores.get(domain,[5])[-5:]) / max(len(self._scores.get(domain,[5])[-5:]),1):.1f}/10
Mastered domains: {self._state['domains_mastered']}

Rules for difficulty {diff_clamp}:
- 1-3: Basic questions with clear answers
- 4-6: Multi-step reasoning, requires planning
- 7-8: Novel problems, requires synthesis of multiple concepts
- 9-10: Research-level, ambiguous, requires creativity

Return JSON only:
{{
  "question": "...",
  "expected_approach": "step by step approach description",
  "difficulty": {diff_clamp},
  "scoring_criteria": ["criterion 1", "criterion 2", "criterion 3"],
  "domain": "{domain}",
  "id": "unique_id"
}}"""

        raw = self._call_luokai(challenger_prompt, challenger_system, max_tokens=400)

        # Parse JSON
        try:
            import re
            json_match = re.search(r'\{[\s\S]+\}', raw)
            if json_match:
                challenge = json.loads(json_match.group())
                challenge["id"]         = hashlib.md5(challenge.get("question","").encode()).hexdigest()[:8]
                challenge["generated"]  = datetime.now().isoformat()
                challenge["difficulty"] = diff_clamp
                return challenge
        except Exception:
            pass

        # Fallback challenge
        fallbacks = {
            "reasoning":       "If a farmer has 3 fields and plants corn in half of them, then plants wheat in half of what's left, and the rest gets beans — what fraction of total fields has beans?",
            "coding":          "Write a Python function that finds the longest palindromic substring in O(n) time.",
            "math":            "Prove that the sum of angles in any triangle is always 180 degrees using only Euclidean geometry.",
            "language":        "Explain the difference between 'affect' and 'effect' with 5 example sentences each.",
            "planning":        "Plan a 3-day trip to Tokyo with a $500 budget, including accommodation, food, and 5 activities.",
            "multi_step_logic":"A train leaves at 9am going 60mph. Another leaves at 10am going 80mph in the same direction. At what time and distance does the second train catch the first?",
        }
        q = fallbacks.get(domain, f"Explain {domain} with a concrete real-world example.")
        return {
            "id": hashlib.md5(q.encode()).hexdigest()[:8],
            "question": q,
            "expected_approach": "Think step by step, show work",
            "difficulty": diff_clamp,
            "scoring_criteria": ["correctness", "reasoning quality", "completeness"],
            "domain": domain,
            "generated": datetime.now().isoformat(),
        }

    # ══════════════════════════════════════════════════════
    #  LUOKAI SOLVER — AI attempts the challenge
    # ══════════════════════════════════════════════════════
    def solve_challenge(self, challenge: Dict) -> Dict:
        """LUOKAI attempts to solve the challenge using ToT reasoning."""
        system = """You are LUOKAI, an advanced AI agent in LuoOS.
Solve the given challenge thoroughly. Show your reasoning step by step.
Be precise, creative, and comprehensive."""

        # Multi-path reasoning (Tree of Thought approach from the zip)
        paths = []
        for approach in ["analytical", "creative", "systematic"]:
            prompt = f"""Challenge: {challenge['question']}

Approach this from a {approach} angle:
1. First, understand what's being asked
2. Break it down into sub-problems
3. Solve each part
4. Synthesize a complete answer

Domain: {challenge['domain']} | Difficulty: {challenge['difficulty']}/10"""

            response = self._call_luokai(prompt, system, max_tokens=600)
            paths.append({"approach": approach, "response": response})

        # Synthesize best answer from all paths
        synthesis_prompt = f"""I have three approaches to this challenge:

Challenge: {challenge['question']}

Approach 1 (Analytical): {paths[0]['response'][:300]}
Approach 2 (Creative): {paths[1]['response'][:300]}
Approach 3 (Systematic): {paths[2]['response'][:300]}

Synthesize these into the single best, most complete answer:"""

        final_answer = self._call_luokai(synthesis_prompt, system, max_tokens=800)

        return {
            "challenge_id": challenge["id"],
            "domain":       challenge["domain"],
            "difficulty":   challenge["difficulty"],
            "answer":       final_answer,
            "paths":        paths,
            "timestamp":    datetime.now().isoformat(),
        }

    # ══════════════════════════════════════════════════════
    #  EVALUATOR — scores the AI's answer
    # ══════════════════════════════════════════════════════
    def evaluate_answer(self, challenge: Dict, solution: Dict) -> Dict:
        """EVALUATOR scores LUOKAI's answer 0-10."""
        evaluator_system = """You are an objective EVALUATOR in a co-evolution system.
Score an AI's answer to a challenge. Be fair but demanding.
Return ONLY valid JSON."""

        eval_prompt = f"""Evaluate this AI answer:

CHALLENGE: {challenge['question']}
DOMAIN: {challenge['domain']} | DIFFICULTY: {challenge['difficulty']}/10
EXPECTED APPROACH: {challenge.get('expected_approach','')}
SCORING CRITERIA: {challenge.get('scoring_criteria',[])}

AI ANSWER: {solution['answer'][:800]}

Score on these dimensions (0-10 each):
- correctness: Is the answer factually/logically correct?
- reasoning: Does it show clear step-by-step thinking?
- completeness: Does it address all parts of the question?
- quality: Is it well-explained and precise?

Return JSON:
{{
  "correctness": 7,
  "reasoning": 8,
  "completeness": 6,
  "quality": 7,
  "overall": 7.0,
  "feedback": "What was good and what was wrong",
  "improvement_hint": "How LUOKAI should improve this specific type of question"
}}"""

        raw = self._call_luokai(eval_prompt, evaluator_system, max_tokens=400)

        try:
            import re
            m = re.search(r'\{[\s\S]+\}', raw)
            if m:
                scores = json.loads(m.group())
                # Calculate overall if not provided
                if "overall" not in scores:
                    dims = ["correctness","reasoning","completeness","quality"]
                    scores["overall"] = sum(scores.get(d,5) for d in dims) / len(dims)
                scores["overall"] = max(0, min(10, float(scores["overall"])))
                return scores
        except Exception:
            pass

        # Heuristic fallback
        answer_len = len(solution.get("answer",""))
        base_score = min(8.0, 3.0 + (answer_len / 200))
        return {
            "correctness": base_score,
            "reasoning":   base_score * 0.9,
            "completeness": base_score * 0.85,
            "quality":     base_score * 0.95,
            "overall":     base_score,
            "feedback":    "Evaluation model offline — heuristic scoring used",
            "improvement_hint": "Keep providing detailed, structured answers",
        }

    # ══════════════════════════════════════════════════════
    #  ADAPTATION — AI learns from failures
    # ══════════════════════════════════════════════════════
    def adapt_from_failure(self, challenge: Dict, solution: Dict, evaluation: Dict):
        """Record failures and generate improvement hints."""
        score = evaluation.get("overall", 5.0)

        # Store failure for fine-tuning
        if score < 6.0:
            failure = {
                "challenge":   challenge,
                "solution":    solution,
                "evaluation":  evaluation,
                "timestamp":   datetime.now().isoformat(),
                "lesson":      evaluation.get("improvement_hint",""),
            }
            self._failures.append(failure)

            # Save for potential fine-tuning with Axolotl/PEFT
            failures_file = self.data_dir / "training_failures.jsonl"
            with open(failures_file, "a") as f:
                # Format as instruction-following training pair
                training_pair = {
                    "instruction": challenge["question"],
                    "input":       f"Domain: {challenge['domain']}, Difficulty: {challenge['difficulty']}/10",
                    "output":      f"[IMPROVED APPROACH]\n{evaluation.get('improvement_hint','')}\n\n"
                                   f"[FEEDBACK]\n{evaluation.get('feedback','')}",
                }
                f.write(json.dumps(training_pair) + "\n")

            print(f"  [CoEvo] Failure logged for fine-tuning (score={score:.1f})")

    # ══════════════════════════════════════════════════════
    #  DIFFICULTY ADAPTATION — harder as AI improves
    # ══════════════════════════════════════════════════════
    def _adapt_difficulty(self, domain: str, new_score: float):
        """Increase difficulty if AI is consistently scoring high."""
        scores = self._scores[domain]
        if len(scores) < 3:
            return

        avg_recent = sum(scores[-3:]) / 3

        if avg_recent >= 8.0 and self.DIFFICULTY[domain] < 10:
            self.DIFFICULTY[domain] = min(10, self.DIFFICULTY[domain] + 1)
            print(f"  [CoEvo] 📈 {domain} difficulty: {self.DIFFICULTY[domain]-1} → {self.DIFFICULTY[domain]}")
            if domain not in self._state["domains_mastered"] and avg_recent >= 9.0:
                self._state["domains_mastered"].append(domain)
                print(f"  [CoEvo] 🏆 Domain mastered: {domain}!")

        elif avg_recent < 5.0 and self.DIFFICULTY[domain] > 1:
            self.DIFFICULTY[domain] = max(1, self.DIFFICULTY[domain] - 1)
            print(f"  [CoEvo] 📉 {domain} difficulty decreased to {self.DIFFICULTY[domain]}")

    def _pick_next_domain(self) -> str:
        """Pick next domain to focus on (weakest area)."""
        domain_scores = {}
        for domain in self.DOMAINS:
            scores = self._scores.get(domain, [5.0])
            domain_scores[domain] = sum(scores[-5:]) / max(len(scores[-5:]), 1)
        # Focus on weakest domain
        return min(domain_scores, key=domain_scores.get)

    # ══════════════════════════════════════════════════════
    #  RUN ONE EVOLUTION CYCLE
    # ══════════════════════════════════════════════════════
    def run_cycle(self) -> Dict:
        """Run one complete co-evolution cycle: challenge → solve → evaluate → adapt."""
        domain    = self._state["current_focus"]
        difficulty = self.DIFFICULTY[domain]

        print(f"\n[CoEvo] ━━━ Cycle #{self._state['total_runs']+1} | {domain.upper()} | Difficulty {difficulty}/10 ━━━")

        # 1. CHALLENGER generates test
        print("[CoEvo] 🎯 CHALLENGER generating challenge...")
        challenge = self.generate_challenge(domain, difficulty)
        print(f"[CoEvo] Question: {challenge['question'][:80]}...")

        # 2. LUOKAI solves it
        print("[CoEvo] 🧠 LUOKAI solving...")
        t0       = time.time()
        solution = self.solve_challenge(challenge)
        solve_t  = time.time() - t0
        print(f"[CoEvo] Solution generated ({solve_t:.1f}s): {solution['answer'][:80]}...")

        # 3. EVALUATOR scores it
        print("[CoEvo] 📊 EVALUATOR scoring...")
        evaluation = self.evaluate_answer(challenge, solution)
        score      = evaluation.get("overall", 5.0)
        print(f"[CoEvo] Score: {score:.1f}/10 | {evaluation.get('feedback','')[:60]}")

        # 4. Update scores and adapt
        self._scores[domain].append(score)
        self._adapt_difficulty(domain, score)

        # 5. Learn from failures
        self.adapt_from_failure(challenge, solution, evaluation)

        # 6. Update global AI score
        all_recent = [s for scores in self._scores.values() for s in scores[-3:]]
        self._state["ai_score"] = sum(all_recent) / max(len(all_recent), 1)

        # 7. Pick next domain
        self._state["total_runs"]    += 1
        self._state["sessions"]      += 1
        self._state["current_focus"]  = self._pick_next_domain()

        # 8. Log cycle
        cycle_result = {
            "cycle":      self._state["total_runs"],
            "domain":     domain,
            "difficulty": difficulty,
            "score":      score,
            "ai_score":   self._state["ai_score"],
            "timestamp":  datetime.now().isoformat(),
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(cycle_result) + "\n")

        self._save_state()

        # Notify callbacks
        for cb in self._callbacks:
            try: cb(cycle_result)
            except Exception: pass

        print(f"[CoEvo] ✅ Cycle done | AI score: {self._state['ai_score']:.1f}/10 | Next: {self._state['current_focus']}")
        return cycle_result

    # ══════════════════════════════════════════════════════
    #  CONTINUOUS EVOLUTION LOOP
    # ══════════════════════════════════════════════════════
    def start_continuous(self, interval_seconds: int = 300):
        """Run evolution cycles continuously in background. Never stops."""
        self._running = True
        def _loop():
            print(f"[CoEvo] 🔄 Continuous evolution started (every {interval_seconds}s)")
            while self._running:
                try:
                    self.run_cycle()
                except Exception as e:
                    print(f"[CoEvo] Error in cycle: {e}")
                # Sleep between cycles
                for _ in range(interval_seconds):
                    if not self._running: break
                    time.sleep(1)
        t = threading.Thread(target=_loop, daemon=True, name="CoEvo")
        t.start()
        return t

    def stop(self):
        self._running = False

    def on_cycle(self, callback: Callable):
        """Register callback for each completed cycle."""
        self._callbacks.append(callback)

    def stats(self) -> Dict:
        return {
            "ai_score":         round(self._state["ai_score"], 2),
            "total_runs":       self._state["total_runs"],
            "current_focus":    self._state["current_focus"],
            "domains_mastered": self._state["domains_mastered"],
            "difficulty_levels": self.DIFFICULTY,
            "failures_logged":  len(self._failures),
            "domain_scores":    {d: round(sum(s[-5:])/max(len(s[-5:]),1),1) for d,s in self._scores.items()},
        }

    def generate_training_data(self, output_file: str = None) -> str:
        """Generate training data from failures for Axolotl fine-tuning."""
        src  = self.data_dir / "training_failures.jsonl"
        dest = output_file or str(self.data_dir / "luokai_finetune_data.jsonl")
        if src.exists():
            import shutil
            shutil.copy(src, dest)
            lines = sum(1 for _ in open(dest))
            return f"Generated {lines} training examples → {dest}"
        return "No failures logged yet — run some cycles first"


# ── Standalone test ──────────────────────────────────────────────────
if __name__ == "__main__":
    engine = CoEvoEngine()
    # Run 3 cycles as demo
    for i in range(3):
        result = engine.run_cycle()
        time.sleep(2)
    print("\nFinal stats:", json.dumps(engine.stats(), indent=2))
