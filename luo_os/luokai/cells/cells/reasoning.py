#!/usr/bin/env python3
"""
luokai/cells/reasoning.py — Reasoning Cells
============================================
Port of reasoning-cells.js from the cell archive.
Provides logical reasoning without any external model.

Cell types:
  Deduction:  ModusPonens, ModusTollens, Syllogism, Hypothetical
  Induction:  Generalization, PatternRecognition, StatisticalInference
  Abduction:  BestExplanation, HypothesisGeneration, DiagnosticReasoning
  Analogy:    StructuralMapping, AnalogyEvaluation
  Causal:     CauseEffect, CounterFactual, Intervention
"""
import re
from typing import Any, List, Dict, Optional
from .base import BaseCell


# ══════════════════════════════════════════════════════════════════
# DEDUCTION CELLS
# ══════════════════════════════════════════════════════════════════

class ModusPonensCell(BaseCell):
    """If P then Q. P is true. Therefore Q. (Forward inference)"""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if not isinstance(signal, dict):
            return signal
        p = signal.get("premise")
        rule = signal.get("rule")   # "if X then Y" form
        if p and rule:
            # Extract conclusion from rule
            match = re.search(r"if (.+) then (.+)", rule, re.IGNORECASE)
            if match and p.lower().strip() in match.group(1).lower():
                return {"conclusion": match.group(2).strip(), "method": "modus_ponens", "confidence": 0.95}
        return signal

    def infer(self, premise: str, rules: List[str]) -> Optional[str]:
        """Apply modus ponens across a set of rules."""
        p_lower = premise.lower()
        for rule in rules:
            m = re.search(r"if (.+?) then (.+)", rule, re.IGNORECASE)
            if m and p_lower in m.group(1).lower():
                self.state += 1
                return m.group(2).strip()
        return None


class ModusTollensCell(BaseCell):
    """If P then Q. Q is false. Therefore P is false. (Backward inference)"""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if not isinstance(signal, dict):
            return signal
        not_q = signal.get("not_consequent")
        rule = signal.get("rule")
        if not_q and rule:
            m = re.search(r"if (.+) then (.+)", rule, re.IGNORECASE)
            if m and not_q.lower() in m.group(2).lower():
                return {"conclusion": f"NOT {m.group(1).strip()}", "method": "modus_tollens", "confidence": 0.9}
        return signal


class SyllogismCell(BaseCell):
    """All A are B. X is A. Therefore X is B."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def apply(self, major: str, minor: str) -> Optional[str]:
        """
        major: 'All dogs are mammals'
        minor: 'Rex is a dog'
        → 'Rex is a mammal'
        """
        m_all = re.match(r"All (\w+) are (\w+)", major, re.IGNORECASE)
        m_is  = re.match(r"(\w+) is (?:a |an )?(\w+)", minor, re.IGNORECASE)
        if m_all and m_is and m_is.group(2).lower() == m_all.group(1).lower():
            self.state += 1
            return f"{m_is.group(1)} is a {m_all.group(2)}"
        return None


class HypotheticalCell(BaseCell):
    """Reasoning from hypothetical conditions."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def evaluate(self, condition: str, consequence: str, is_condition_met: bool) -> Dict:
        if is_condition_met:
            return {"result": consequence, "certainty": "likely", "type": "hypothetical_affirmed"}
        return {"result": f"Cannot conclude: {consequence}", "certainty": "unknown", "type": "hypothetical_unmet"}


# ══════════════════════════════════════════════════════════════════
# INDUCTION CELLS
# ══════════════════════════════════════════════════════════════════

class GeneralizationCell(BaseCell):
    """Infer general rules from specific examples."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def generalize(self, examples: List[Dict]) -> Optional[str]:
        """Find common pattern across examples."""
        if not examples:
            return None
        # Find shared keys with same values
        if not isinstance(examples[0], dict):
            return None
        shared = {}
        first = examples[0]
        for k, v in first.items():
            if all(ex.get(k) == v for ex in examples[1:]):
                shared[k] = v
        if shared:
            self.state += 1
            parts = [f"{k}={v}" for k, v in list(shared.items())[:3]]
            return f"Pattern: {', '.join(parts)} (from {len(examples)} examples)"
        return None


class PatternRecognitionCell(BaseCell):
    """Recognize recurring patterns in sequences."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, list) and len(signal) >= 3:
            # Look for arithmetic pattern
            if all(isinstance(x, (int, float)) for x in signal):
                diffs = [signal[i+1]-signal[i] for i in range(len(signal)-1)]
                if len(set(diffs)) == 1:
                    return {"pattern": "arithmetic", "diff": diffs[0], "next": signal[-1]+diffs[0]}
        return signal


class StatisticalInferenceCell(BaseCell):
    """Draw statistical conclusions from data."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def summarize(self, values: List[float]) -> Dict:
        if not values:
            return {}
        n = len(values)
        mean = sum(values) / n
        sorted_v = sorted(values)
        median = sorted_v[n//2]
        variance = sum((x-mean)**2 for x in values) / n
        return {"n": n, "mean": round(mean,4), "median": median,
                "min": min(values), "max": max(values), "std": round(variance**0.5,4)}


# ══════════════════════════════════════════════════════════════════
# ABDUCTION CELLS
# ══════════════════════════════════════════════════════════════════

class BestExplanationCell(BaseCell):
    """Infer the best explanation for an observation."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def explain(self, observation: str, candidates: List[Dict]) -> Optional[Dict]:
        """
        Pick the best explanation from candidates.
        candidates: [{"explanation": str, "probability": float, "simplicity": float}]
        """
        if not candidates:
            return None
        scored = []
        for c in candidates:
            score = c.get("probability", 0.5) * 0.6 + c.get("simplicity", 0.5) * 0.4
            scored.append((score, c))
        scored.sort(key=lambda x: -x[0])
        self.state += 1
        return scored[0][1] if scored else None


class HypothesisGenerationCell(BaseCell):
    """Generate hypotheses from observations."""
    category = "reasoning"

    HYPOTHESIS_TEMPLATES = [
        "Perhaps {observation} is caused by {factor}",
        "It's possible that {factor} leads to {observation}",
        "One explanation for {observation} could be {factor}",
        "Hypothesis: {factor} → {observation}",
    ]

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def generate(self, observation: str, known_factors: List[str]) -> List[str]:
        hypotheses = []
        for factor in known_factors[:4]:
            for tmpl in self.HYPOTHESIS_TEMPLATES[:2]:
                hypotheses.append(tmpl.format(observation=observation, factor=factor))
        self.state += 1
        return hypotheses


class DiagnosticReasoningCell(BaseCell):
    """Diagnose problems from symptoms — like a doctor or debugger."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def diagnose(self, symptoms: List[str], knowledge_base: List[Dict]) -> List[Dict]:
        """
        Match symptoms to known conditions in knowledge_base.
        kb items: {"condition": str, "symptoms": [str], "solution": str}
        """
        results = []
        sym_lower = [s.lower() for s in symptoms]
        for item in knowledge_base:
            known_syms = [s.lower() for s in item.get("symptoms", [])]
            matches = sum(1 for s in sym_lower if any(s in ks or ks in s for ks in known_syms))
            if matches > 0:
                score = matches / max(len(known_syms), len(sym_lower))
                results.append({"condition": item["condition"], "confidence": score,
                                 "solution": item.get("solution","")})
        self.state += 1
        return sorted(results, key=lambda x: -x["confidence"])[:3]


# ══════════════════════════════════════════════════════════════════
# ANALOGY CELLS
# ══════════════════════════════════════════════════════════════════

class StructuralMappingCell(BaseCell):
    """Map relationships from source domain to target domain."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def map_analogy(self, source: Dict, target_domain: str) -> str:
        """
        source: {"A": "atom", "B": "nucleus", "relation": "A orbits B"}
        target_domain: "solar system"
        → "planet orbits sun" (by analogy)
        """
        relation = source.get("relation", "")
        self.state += 1
        return f"By analogy to {source.get('A','')}:{source.get('B','')}, in {target_domain}: {relation}"


class AnalogyEvaluationCell(BaseCell):
    """Evaluate strength of an analogy."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def evaluate(self, source_features: List[str], target_features: List[str]) -> Dict:
        shared = set(source_features) & set(target_features)
        total = set(source_features) | set(target_features)
        strength = len(shared) / len(total) if total else 0
        self.state += 1
        return {
            "shared_features": list(shared),
            "strength": round(strength, 3),
            "assessment": "strong" if strength > 0.6 else "moderate" if strength > 0.3 else "weak"
        }


# ══════════════════════════════════════════════════════════════════
# CAUSAL CELLS
# ══════════════════════════════════════════════════════════════════

class CauseEffectCell(BaseCell):
    """Model cause-effect relationships."""
    category = "reasoning"

    def __init__(self, name: str):
        super().__init__(name)
        self._causal_map: Dict[str, List[str]] = {}  # cause → [effects]

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def learn_causal(self, cause: str, effects: List[str]) -> None:
        c = cause.lower()
        if c not in self._causal_map:
            self._causal_map[c] = []
        self._causal_map[c].extend(effects)

    def predict_effects(self, cause: str) -> List[str]:
        self.state += 1
        c = cause.lower()
        # Direct match
        if c in self._causal_map:
            return self._causal_map[c]
        # Partial match
        for k, v in self._causal_map.items():
            if k in c or c in k:
                return v
        return []


class CounterFactualCell(BaseCell):
    """Reason about what would happen if things were different."""
    category = "reasoning"

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def reason(self, actual: str, counterfactual: str, known_effects: Dict[str, str]) -> str:
        self.state += 1
        # Look for the actual event in known effects
        for cause, effect in known_effects.items():
            if cause.lower() in actual.lower():
                return (f"If '{counterfactual}' instead of '{actual}', "
                        f"then '{effect}' might not have occurred.")
        return f"If '{counterfactual}' instead of '{actual}', the outcome is uncertain."


# ══════════════════════════════════════════════════════════════════
# REASONING ENGINE — orchestrates all cells
# ══════════════════════════════════════════════════════════════════

class ReasoningEngine:
    """
    Orchestrates all reasoning cells.
    LUOKAI's logical reasoning — no LLM needed.
    """

    def __init__(self):
        # Deduction
        self.modus_ponens    = ModusPonensCell("modus_ponens")
        self.modus_tollens   = ModusTollensCell("modus_tollens")
        self.syllogism       = SyllogismCell("syllogism")
        self.hypothetical    = HypotheticalCell("hypothetical")

        # Induction
        self.generalization  = GeneralizationCell("generalization")
        self.pattern_recog   = PatternRecognitionCell("pattern_recognition")
        self.statistical     = StatisticalInferenceCell("statistical")

        # Abduction
        self.best_explain    = BestExplanationCell("best_explanation")
        self.hypothesis_gen  = HypothesisGenerationCell("hypothesis_generation")
        self.diagnostic      = DiagnosticReasoningCell("diagnostic")

        # Analogy
        self.struct_mapping  = StructuralMappingCell("structural_mapping")
        self.analogy_eval    = AnalogyEvaluationCell("analogy_evaluation")

        # Causal
        self.cause_effect    = CauseEffectCell("cause_effect")
        self.counterfactual  = CounterFactualCell("counterfactual")

        self.cells = [
            self.modus_ponens, self.modus_tollens, self.syllogism,
            self.hypothetical, self.generalization, self.pattern_recog,
            self.statistical, self.best_explain, self.hypothesis_gen,
            self.diagnostic, self.struct_mapping, self.analogy_eval,
            self.cause_effect, self.counterfactual,
        ]
        print(f"[ReasoningEngine] {len(self.cells)} reasoning cells active")

    def reason(self, query: str, context: Dict = None) -> str:
        """Apply best reasoning approach to a query."""
        q = query.lower()
        ctx = context or {}

        # Pattern: "if ... then ..."
        if "if " in q and " then " in q:
            m = re.search(r"if (.+?) then (.+?)(?:\?|$)", q)
            if m:
                return f"Logical inference: if '{m.group(1)}' → '{m.group(2)}'. This is a conditional. Verify the antecedent to confirm the consequent."

        # Pattern: "why ..." → diagnostic/causal
        if q.startswith("why "):
            subject = q[4:].strip()
            effects = self.cause_effect.predict_effects(subject)
            if effects:
                return f"Possible causes of '{subject}': {'; '.join(effects[:3])}"
            hypotheses = self.hypothesis_gen.generate(subject, ["environment", "input", "state", "dependency"])
            return "Reasoning by abduction:\n" + "\n".join(f"  • {h}" for h in hypotheses[:3])

        # Pattern: what/how → deductive answer
        if any(q.startswith(w) for w in ("what ", "how ")):
            results = []
            for cell in self.cells:
                hits = cell.search(query, limit=1)
                if hits:
                    results.append(hits[0])
            if results:
                r = results[0]
                return json.dumps(r, indent=2)[:400] if isinstance(r, dict) else str(r)[:400]

        # Default: generalize from learned data
        for cell in self.cells:
            hits = cell.search(query, limit=2)
            if hits:
                return f"From {cell.name}: {json.dumps(hits[0])[:300]}"

        return f"Reasoning about '{query}': insufficient data. Learning from this query."

    def status(self) -> Dict:
        return {
            "cells": len(self.cells),
            "total_activations": sum(c._activations for c in self.cells),
            "total_learned": sum(len(c.specialized_data) for c in self.cells),
            "cell_status": {c.name: c.status() for c in self.cells},
        }


import json  # needed in reason()
