#!/usr/bin/env python3
"""
luokai/cells/neural/interpreter.py
=====================================
SpikeInterpreter — translates raw spike patterns into LUOKAI cognitive signals.

The MEA has 64 channels arranged in an 8×8 grid.
Different spatial patterns of activity map to different cognitive states.
"""
import math
import collections
from typing import Dict, List, Optional, Tuple
from ..base import BaseCell
from .bridge import SpikePattern


# MEA 8×8 grid — channel positions
# Channels 1-64 mapped to (row, col) 0-7
def channel_to_xy(ch: int) -> Tuple[int, int]:
    """Map channel number (1-64) to grid position (row, col)."""
    idx = ch - 1
    return idx // 8, idx % 8


def channels_to_quadrant(channels: List[int]) -> str:
    """Identify which quadrant of the MEA is most active."""
    if not channels:
        return "none"
    rows = [channel_to_xy(c)[0] for c in channels]
    cols = [channel_to_xy(c)[1] for c in channels]
    avg_row = sum(rows) / len(rows)
    avg_col = sum(cols) / len(cols)

    if avg_row < 4 and avg_col < 4:   return "top_left"
    if avg_row < 4 and avg_col >= 4:  return "top_right"
    if avg_row >= 4 and avg_col < 4:  return "bottom_left"
    return "bottom_right"


class SpikeInterpreter(BaseCell):
    """
    Translates spike patterns → LUOKAI intent signals.

    Maps:
      Burst (>200Hz)           → "HIGH_ACTIVITY" — excited/engaged state
      Synchronous (many ch)    → "SYNCHRONIZED"  — coherent processing
      Sparse (<5Hz)            → "REST"           — low activity / idle
      Focal (few channels)     → "FOCAL"          — localised processing
      Distributed (normal)     → "ACTIVE"         — normal cognition
      Rhythm detected          → "RHYTHMIC"       — oscillatory pattern

    Spatial mapping:
      Top half active          → "SENSORY"        — input processing
      Bottom half active       → "MOTOR"          — output generation
      Left half                → "ANALYTICAL"     — structured thinking
      Right half               → "CREATIVE"       — associative thinking
    """
    category = "neural"

    def __init__(self, name: str = "spike_interpreter"):
        super().__init__(name)
        self._history: collections.deque = collections.deque(maxlen=200)
        self._rhythm_detector = RhythmDetector()
        self._current_signal  = "REST"

    def process(self, signal) -> str:
        """Process a SpikePattern and return a cognitive signal string."""
        super().process(signal)
        if isinstance(signal, SpikePattern):
            return self.interpret(signal)
        if isinstance(signal, dict):
            # dict version of SpikePattern
            rate   = signal.get("rate_hz", 0)
            ptype  = signal.get("pattern", "unknown")
            chs    = signal.get("channels", [])
            p = SpikePattern(chs, [], rate, ptype)
            return self.interpret(p)
        return self._current_signal

    def interpret(self, pattern: SpikePattern) -> str:
        """Full interpretation pipeline."""
        # 1. Base signal from pattern type
        base = self._classify_base(pattern)

        # 2. Spatial modifier
        spatial = channels_to_quadrant(pattern.channels)

        # 3. Rhythm detection
        is_rhythmic = self._rhythm_detector.update(pattern.rate_hz)

        # 4. Combine into cognitive signal
        signal = self._combine(base, spatial, is_rhythmic, pattern)

        # 5. Store and return
        self._history.append({
            "signal":   signal,
            "pattern":  pattern.pattern_type,
            "rate":     pattern.rate_hz,
            "spatial":  spatial,
            "rhythmic": is_rhythmic,
        })
        self._current_signal = signal
        self.state += 1
        return signal

    def _classify_base(self, pattern: SpikePattern) -> str:
        r = pattern.rate_hz
        p = pattern.pattern_type

        if p == "burst" or r > 200:       return "HIGH_ACTIVITY"
        if p == "synchronous" and r > 80: return "SYNCHRONIZED"
        if p == "sparse" or r < 5:        return "REST"
        if p == "focal":                   return "FOCAL"
        if p == "silent":                  return "SILENT"
        return "ACTIVE"

    def _combine(self, base: str, spatial: str,
                 rhythmic: bool, pattern: SpikePattern) -> str:
        """Combine base signal with spatial and temporal context."""
        if base == "SILENT":
            return "SILENT"
        if base == "REST":
            return "RESTING"
        if rhythmic:
            return f"RHYTHMIC_{base}"
        if base == "HIGH_ACTIVITY":
            return "ENGAGED"
        if base == "SYNCHRONIZED":
            # Map spatial to cognitive domain
            quad_map = {
                "top_left":     "ANALYTICAL_FOCUS",
                "top_right":    "CREATIVE_FOCUS",
                "bottom_left":  "MOTOR_PLANNING",
                "bottom_right": "SENSORY_INTEGRATION",
            }
            return quad_map.get(spatial, "FOCUSED")
        return base

    def signal_to_luokai_context(self, signal: str) -> Dict:
        """
        Convert a neural signal to a LUOKAI context dict.
        Used to inject neural state into LUOKAI's response generation.
        """
        context_map = {
            "RESTING":              {"mood": "calm",     "verbosity": "minimal"},
            "ACTIVE":               {"mood": "neutral",  "verbosity": "normal"},
            "ENGAGED":              {"mood": "alert",    "verbosity": "detailed"},
            "FOCUSED":              {"mood": "focused",  "verbosity": "precise"},
            "ANALYTICAL_FOCUS":     {"mood": "logical",  "verbosity": "structured"},
            "CREATIVE_FOCUS":       {"mood": "creative", "verbosity": "exploratory"},
            "RHYTHMIC_ACTIVE":      {"mood": "rhythmic", "verbosity": "normal"},
            "SYNCHRONIZED":         {"mood": "coherent", "verbosity": "concise"},
            "SILENT":               {"mood": "quiet",    "verbosity": "minimal"},
            "HIGH_ACTIVITY":        {"mood": "excited",  "verbosity": "verbose"},
        }
        return context_map.get(signal, {"mood": "neutral", "verbosity": "normal"})

    def get_trend(self) -> str:
        """Get the trend in neural activity over recent history."""
        if len(self._history) < 5:
            return "stable"
        recent_rates = [h["rate"] for h in list(self._history)[-10:]]
        if len(recent_rates) < 2:
            return "stable"
        trend = recent_rates[-1] - recent_rates[0]
        if trend > 20:   return "increasing"
        if trend < -20:  return "decreasing"
        return "stable"

    def summary(self) -> Dict:
        """Summary of recent neural interpretation."""
        if not self._history:
            return {"signal": "REST", "trend": "stable"}
        recent = list(self._history)[-20:]
        signals = [h["signal"] for h in recent]
        dominant = max(set(signals), key=signals.count)
        return {
            "current_signal":  self._current_signal,
            "dominant_signal": dominant,
            "trend":           self.get_trend(),
            "sample_count":    len(self._history),
        }


class RhythmDetector:
    """
    Detects oscillatory rhythms in spike rate (theta, alpha, beta, gamma).
    Biological neurons naturally exhibit these rhythms.
    """
    BANDS = {
        "theta": (4, 8),     # Hz — memory, navigation
        "alpha": (8, 12),    # Hz — relaxed awareness
        "beta":  (12, 30),   # Hz — active thinking
        "gamma": (30, 100),  # Hz — binding, consciousness
    }

    def __init__(self, history_len: int = 30):
        self._rates: collections.deque = collections.deque(maxlen=history_len)
        self._detected_band: Optional[str] = None

    def update(self, rate_hz: float) -> bool:
        """Update with new rate. Returns True if rhythm detected."""
        self._rates.append(rate_hz)
        if len(self._rates) < 10:
            return False

        avg = sum(self._rates) / len(self._rates)
        for band, (lo, hi) in self.BANDS.items():
            if lo <= avg <= hi:
                self._detected_band = band
                return True

        self._detected_band = None
        return False

    @property
    def band(self) -> Optional[str]:
        return self._detected_band
