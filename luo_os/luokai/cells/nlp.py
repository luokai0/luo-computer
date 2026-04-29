#!/usr/bin/env python3
"""
luokai/cells/nlp.py — NLP Cells
================================
Port of nlp-cells.js — natural language processing without external libs.

Cells: Tokenizer, POS, NER, Parser, IntentClassifier, SentimentAnalyzer,
       SemanticSimilarity, ContextTracker
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseCell


# ══════════════════════════════════════════════════════════════════
# TOKENIZER CELL
# ══════════════════════════════════════════════════════════════════

class TokenizerCell(BaseCell):
    """Tokenizes text into words, sentences, subwords."""
    category = "nlp"

    STOP_WORDS = {
        "a","an","the","is","are","was","were","be","been","being",
        "have","has","had","do","does","did","will","would","could",
        "should","may","might","shall","can","need","dare","ought",
        "used","to","of","in","on","at","by","for","with","from",
        "and","or","but","not","no","nor","so","yet","both","either",
        "this","that","these","those","it","its","it's","i","me","my",
        "you","your","he","his","she","her","they","their","we","our",
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.tokenize(signal)
        return signal

    def tokenize(self, text: str) -> List[str]:
        """Split text into tokens."""
        tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b|\d+\.?\d*|[^\w\s]", text)
        return tokens

    def words(self, text: str) -> List[str]:
        """Just alphabetic words."""
        return re.findall(r"\b[a-zA-Z]+\b", text.lower())

    def meaningful_words(self, text: str) -> List[str]:
        """Words minus stop words."""
        return [w for w in self.words(text) if w not in self.STOP_WORDS and len(w) > 2]

    def sentences(self, text: str) -> List[str]:
        """Split into sentences."""
        return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


# ══════════════════════════════════════════════════════════════════
# NER CELL (Named Entity Recognition)
# ══════════════════════════════════════════════════════════════════

class NERCell(BaseCell):
    """Recognize named entities: languages, frameworks, errors, concepts."""
    category = "nlp"

    LANGUAGES = {
        "python","javascript","typescript","rust","go","java","c++","c#",
        "ruby","swift","kotlin","scala","haskell","erlang","elixir","r",
        "matlab","julia","lua","perl","php","dart","sql","bash","shell",
        "html","css","sass","less","graphql","yaml","json","xml","toml",
    }
    FRAMEWORKS = {
        "react","vue","angular","svelte","nextjs","nuxt","express","fastapi",
        "django","flask","rails","spring","laravel","gin","echo","fiber",
        "tensorflow","pytorch","keras","scikit","pandas","numpy","scipy",
        "docker","kubernetes","terraform","ansible","jenkins","github","gitlab",
        "postgresql","mysql","mongodb","redis","elasticsearch","kafka","rabbitmq",
    }
    ERROR_TYPES = {
        "syntaxerror","typeerror","valueerror","keyerror","indexerror",
        "attributeerror","nameerror","importerror","runtimeerror","ioerror",
        "nullpointerexception","segfault","stackoverflow","outofmemory",
        "404","500","401","403","timeout","connectionerror",
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.extract(signal)
        return signal

    def extract(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text."""
        t_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", t_lower))

        found_langs  = list(words & self.LANGUAGES)
        found_frames = list(words & self.FRAMEWORKS)
        found_errors = [e for e in self.ERROR_TYPES if e in t_lower]

        # Also check learned entities
        learned_langs = []
        for item in self.specialized_data:
            if isinstance(item, dict) and "language" in item:
                lang = item["language"].lower()
                if lang in t_lower:
                    learned_langs.append(lang)

        return {
            "languages":  list(set(found_langs + learned_langs)),
            "frameworks": found_frames,
            "errors":     found_errors,
        }


# ══════════════════════════════════════════════════════════════════
# INTENT CLASSIFIER CELL (upgrades the one in inference.py)
# ══════════════════════════════════════════════════════════════════

class IntentClassifierCell(BaseCell):
    """
    Advanced intent classification.
    Replaces/augments the regex classifier in inference.py.
    """
    category = "nlp"

    INTENTS = {
        "debug": {
            "keywords": ["error","bug","fix","debug","crash","broken","fails","exception",
                         "traceback","undefined","null","not working","wrong output"],
            "patterns":  [r"\berror\b", r"\bbug\b", r"\bfix\b", r"\bcrash\b"],
        },
        "explain": {
            "keywords": ["what is","explain","how does","what are","describe","tell me",
                         "what's","definition","meaning","understand"],
            "patterns":  [r"\bwhat is\b", r"\bexplain\b", r"\bhow does\b"],
        },
        "implement": {
            "keywords": ["how to","implement","build","create","write","make","code",
                         "example","show me how","tutorial"],
            "patterns":  [r"\bhow (to|do)\b", r"\bimplement\b", r"\bbuild\b"],
        },
        "compare": {
            "keywords": ["difference","vs","versus","compare","better","which","prefer",
                         "pros cons","trade-off","tradeoff"],
            "patterns":  [r"\b(vs|versus)\b", r"\bdifference between\b"],
        },
        "optimize": {
            "keywords": ["slow","optimize","performance","faster","efficient","speed",
                         "memory","latency","throughput","bottleneck"],
            "patterns":  [r"\boptim\w+\b", r"\bperformanc\w+\b", r"\bslow\b"],
        },
        "security": {
            "keywords": ["secure","vulnerability","auth","permission","sql injection",
                         "xss","csrf","sanitize","encrypt","hash","token","jwt"],
            "patterns":  [r"\bsecur\w+\b", r"\bvulnerab\w+\b", r"\bauth\w+\b"],
        },
        "test": {
            "keywords": ["test","testing","unit test","mock","assert","coverage",
                         "pytest","jest","tdd","bdd","spec"],
            "patterns":  [r"\btest\w*\b", r"\bmock\b", r"\bassert\b"],
        },
        "deploy": {
            "keywords": ["deploy","production","docker","kubernetes","ci/cd","pipeline",
                         "release","ship","server","cloud","aws","gcp","azure"],
            "patterns":  [r"\bdeploy\b", r"\bproduc\w+\b", r"\bdocker\b"],
        },
        "algorithm": {
            "keywords": ["algorithm","complexity","big o","sort","search","graph",
                         "dynamic programming","recursion","data structure","hash"],
            "patterns":  [r"\balgorithm\b", r"\bcomplexity\b", r"\bO\([^\)]+\)"],
        },
        "greet": {
            "keywords": ["hi","hello","hey","howdy","good morning","good evening","sup"],
            "patterns":  [r"^(hi|hello|hey|howdy)\b"],
        },
        "status": {
            "keywords": ["status","health","how are you","online","working","running"],
            "patterns":  [r"\bstatus\b", r"\bhealth\b"],
        },
    }

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.classify(signal)
        return signal

    def classify(self, text: str, top_n: int = 1) -> str:
        """Classify text intent, return best match."""
        t = text.lower()
        scores: Dict[str, float] = {}

        for intent, config in self.INTENTS.items():
            score = 0.0
            for kw in config["keywords"]:
                if kw in t:
                    score += 1.0 + (0.5 if t.startswith(kw) else 0)
            for pat in config["patterns"]:
                if re.search(pat, t):
                    score += 1.5
            if score > 0:
                scores[intent] = score

        # Check learned patterns
        for item in self.specialized_data[-200:]:
            if isinstance(item, dict):
                learned_intent = item.get("intent","")
                learned_text   = item.get("text","").lower()
                if learned_intent and learned_text:
                    words = set(t.split()) & set(learned_text.split())
                    if len(words) >= 2:
                        scores[learned_intent] = scores.get(learned_intent, 0) + 0.8

        if not scores:
            return "general"

        sorted_intents = sorted(scores.items(), key=lambda x: -x[1])
        if top_n == 1:
            return sorted_intents[0][0]
        return [i for i, _ in sorted_intents[:top_n]]

    def learn_intent(self, text: str, intent: str) -> None:
        """Learn that this text corresponds to this intent."""
        self.learn({"text": text, "intent": intent})


# ══════════════════════════════════════════════════════════════════
# SENTIMENT CELL
# ══════════════════════════════════════════════════════════════════

class SentimentCell(BaseCell):
    """Detect sentiment: frustrated, curious, satisfied, urgent."""
    category = "nlp"

    POSITIVE = {"great","excellent","perfect","thanks","thank","love","awesome",
                "wonderful","good","nice","helpful","clear","easy","fast","works"}
    NEGATIVE = {"broken","error","fails","wrong","bad","terrible","awful","slow",
                "confused","stuck","help","urgent","critical","asap","please fix"}
    URGENT   = {"asap","urgent","critical","production","down","broken","immediately","now"}
    CURIOUS  = {"why","how","what","explain","understand","curious","wondering","interested"}

    def process(self, signal: Any) -> Any:
        super().process(signal)
        if isinstance(signal, str):
            return self.analyze(signal)
        return signal

    def analyze(self, text: str) -> Dict:
        words = set(text.lower().split())
        pos_score = len(words & self.POSITIVE)
        neg_score = len(words & self.NEGATIVE)
        urgent    = bool(words & self.URGENT)
        curious   = bool(words & self.CURIOUS)

        if urgent:
            sentiment = "urgent"
        elif pos_score > neg_score:
            sentiment = "positive"
        elif neg_score > pos_score:
            sentiment = "negative" if not curious else "frustrated_curious"
        elif curious:
            sentiment = "curious"
        else:
            sentiment = "neutral"

        self.state += 1
        return {
            "sentiment": sentiment,
            "positive_signals": pos_score,
            "negative_signals": neg_score,
            "is_urgent": urgent,
            "is_curious": curious,
        }


# ══════════════════════════════════════════════════════════════════
# CONTEXT TRACKER CELL
# ══════════════════════════════════════════════════════════════════

class ContextTrackerCell(BaseCell):
    """Track conversation context across turns."""
    category = "nlp"

    def __init__(self, name: str):
        super().__init__(name)
        self._turns: List[Dict] = []
        self._entities: Dict[str, str] = {}   # entity → value
        self._topic: Optional[str] = None
        self._language: Optional[str] = None

    def process(self, signal: Any) -> Any:
        super().process(signal)
        return signal

    def update(self, text: str, role: str = "user", entities: Dict = None) -> None:
        """Update context with a new turn."""
        turn = {"role": role, "text": text[:200], "ts": __import__("time").time()}
        if entities:
            self._entities.update(entities.get("languages", {}) and {"language": entities["languages"][0]} or {})
            if entities.get("languages"):
                self._language = entities["languages"][0]
        self._turns.append(turn)
        if len(self._turns) > 20:
            self._turns = self._turns[-16:]

    def get_context(self) -> Dict:
        """Get current conversation context."""
        return {
            "turns": len(self._turns),
            "topic": self._topic,
            "language": self._language,
            "entities": self._entities,
            "recent": [t["text"] for t in self._turns[-3:]],
        }

    def get_language(self) -> Optional[str]:
        return self._language

    def resolve_pronoun(self, text: str) -> str:
        """Replace 'it', 'that' with most recent entity."""
        if not self._entities:
            return text
        last_entity = list(self._entities.values())[-1]
        for pronoun in ["it", "that", "this"]:
            text = re.sub(rf"\b{pronoun}\b", last_entity, text, flags=re.IGNORECASE)
        return text


# ══════════════════════════════════════════════════════════════════
# NLP ENGINE — orchestrates all NLP cells
# ══════════════════════════════════════════════════════════════════

class NLPEngine:
    """Orchestrates all NLP cells for text understanding."""

    def __init__(self):
        self.tokenizer  = TokenizerCell("tokenizer")
        self.ner        = NERCell("ner")
        self.intent     = IntentClassifierCell("intent_classifier")
        self.sentiment  = SentimentCell("sentiment")
        self.context    = ContextTrackerCell("context_tracker")

        self.cells = [self.tokenizer, self.ner, self.intent, self.sentiment, self.context]
        print(f"[NLPEngine] {len(self.cells)} NLP cells active")

    def analyze(self, text: str) -> Dict:
        """Full NLP analysis of a text."""
        tokens   = self.tokenizer.tokenize(text)
        keywords = self.tokenizer.meaningful_words(text)
        entities = self.ner.extract(text)
        intent   = self.intent.classify(text)
        sentiment_data = self.sentiment.analyze(text)

        self.context.update(text, "user", entities)

        return {
            "text":      text,
            "tokens":    len(tokens),
            "keywords":  keywords[:10],
            "intent":    intent,
            "entities":  entities,
            "sentiment": sentiment_data["sentiment"],
            "is_urgent": sentiment_data["is_urgent"],
            "language":  self.context.get_language(),
            "context":   self.context.get_context(),
        }

    def status(self) -> Dict:
        return {
            "cells": len(self.cells),
            "context_turns": len(self.context._turns),
            "tracked_language": self.context.get_language(),
            "learned_intents": len(self.intent.specialized_data),
        }
