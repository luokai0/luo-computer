#!/usr/bin/env python3
"""
luokai/cells/neural/stimulator.py
====================================
StimulusDesigner — converts LUOKAI cognitive decisions into
precise electrode stimulation patterns for the CL1 MEA.

The CL1 MEA stimulates using biphasic pulses:
  Phase 1: cathodic (negative current, depolarises membrane)
  Phase 2: anodic  (positive current, charge balance)

Safe stimulation ranges:
  Amplitude:  0.5 – 3.0 µA
  Phase duration: 80 – 480 µs
  Frequency: 1 – 200 Hz
  Burst size: 1 – 100 pulses
"""
from typing import Dict, List, Optional, Any
from ..base import BaseCell


class StimPulse:
    """Single biphasic stimulation pulse."""
    def __init__(self, channel: int,
                 phase1_us: int = 180, amp1_ua: float = -1.5,
                 phase2_us: int = 180, amp2_ua: float = 1.5):
        self.channel   = channel
        self.phase1_us = phase1_us   # cathodic phase duration µs
        self.amp1_ua   = amp1_ua     # cathodic amplitude µA (negative)
        self.phase2_us = phase2_us   # anodic phase duration µs
        self.amp2_ua   = amp2_ua     # anodic amplitude µA (positive)

    def to_cl_args(self):
        """Return args for cl.StimDesign(phase1_us, amp1, phase2_us, amp2)."""
        return (self.phase1_us, self.amp1_ua, self.phase2_us, self.amp2_ua)

    def charge_density(self) -> float:
        """Charge density in nC — must stay < 20 nC/cm² for safety."""
        charge = abs(self.amp1_ua) * self.phase1_us * 1e-6  # µC
        return charge * 1000  # nC


class StimBurst:
    """A burst of stimulation pulses on one or more channels."""
    def __init__(self, channels: List[int], pulse: StimPulse,
                 count: int = 1, freq_hz: float = 50.0):
        self.channels = channels
        self.pulse    = pulse
        self.count    = count       # number of pulses
        self.freq_hz  = freq_hz     # pulse frequency

    def duration_ms(self) -> float:
        """Total burst duration in milliseconds."""
        if self.count <= 1:
            return (self.pulse.phase1_us + self.pulse.phase2_us) / 1000
        return (self.count / self.freq_hz) * 1000

    def to_dict(self) -> Dict:
        return {
            "channels":    self.channels,
            "phase1_us":   self.pulse.phase1_us,
            "amp_ua":      abs(self.pulse.amp1_ua),
            "count":       self.count,
            "freq_hz":     self.freq_hz,
            "duration_ms": round(self.duration_ms(), 2),
        }


class StimulusDesigner(BaseCell):
    """
    Designs stimulation patterns from LUOKAI cognitive signals.

    LUOKAI says: "reward the neurons for correct behaviour"
    StimulusDesigner says: "send a 5-pulse burst at 50Hz on active channels"

    Preset library (from CL API docs + neuroscience research):
      reward      — reinforcement signal, activating
      error       — mild inhibitory signal
      explore     — low-amplitude distributed exploration
      reinforce   — strong burst for memory consolidation
      probe       — single pulse to test channel responsiveness
      reset       — broad low-amplitude to normalise activity
      entrain     — rhythmic stimulation to synchronise activity
    """
    category = "neural"

    # Safe stimulation limits
    MAX_AMP_UA  = 3.0
    MIN_AMP_UA  = 0.5
    MAX_PHASE_US = 480
    MIN_PHASE_US = 80

    # Preset stimulation patterns
    PRESETS = {
        "reward": {
            "desc":     "Reward signal — reinforces positive behaviour",
            "phase_us": 180, "amp_ua": 1.5,
            "count":    5,   "freq_hz": 50.0,
        },
        "error": {
            "desc":     "Error signal — mild corrective feedback",
            "phase_us": 160, "amp_ua": 0.8,
            "count":    1,   "freq_hz": 1.0,
        },
        "explore": {
            "desc":     "Exploration — low-amp distributed stimulation",
            "phase_us": 200, "amp_ua": 1.0,
            "count":    2,   "freq_hz": 10.0,
        },
        "reinforce": {
            "desc":     "Reinforcement — strong burst for consolidation",
            "phase_us": 200, "amp_ua": 2.0,
            "count":    10,  "freq_hz": 100.0,
        },
        "probe": {
            "desc":     "Single probe pulse to test channel",
            "phase_us": 180, "amp_ua": 1.5,
            "count":    1,   "freq_hz": 1.0,
        },
        "reset": {
            "desc":     "Broad normalisation across array",
            "phase_us": 320, "amp_ua": 0.8,
            "count":    3,   "freq_hz": 5.0,
        },
        "entrain_theta": {
            "desc":     "Theta entrainment (6Hz) — memory/navigation",
            "phase_us": 180, "amp_ua": 1.2,
            "count":    6,   "freq_hz": 6.0,
        },
        "entrain_gamma": {
            "desc":     "Gamma entrainment (40Hz) — binding/attention",
            "phase_us": 160, "amp_ua": 1.0,
            "count":    40,  "freq_hz": 40.0,
        },
        "hello": {
            "desc":     "Hello World — first stimulation",
            "phase_us": 180, "amp_ua": 1.5,
            "count":    1,   "freq_hz": 1.0,
        },
    }

    def __init__(self, name: str = "stimulus_designer"):
        super().__init__(name)
        self._stim_history: List[Dict] = []
        self._total_charge_nc: float = 0.0

    def process(self, signal: Any) -> Optional[StimBurst]:
        """Process a cognitive signal into a StimBurst."""
        super().process(signal)
        if isinstance(signal, str):
            return self.design_from_preset(signal, channels=[27, 28, 35, 36])
        if isinstance(signal, dict):
            preset  = signal.get("type", "probe")
            channels = signal.get("channels", [27])
            return self.design_from_preset(preset, channels)
        return None

    def design_from_preset(self, preset_name: str,
                            channels: List[int],
                            intensity: float = 1.0) -> StimBurst:
        """
        Create a StimBurst from a named preset.

        preset_name — one of the PRESETS keys
        channels    — which MEA channels to stimulate
        intensity   — scale factor 0.5 to 2.0
        """
        preset = self.PRESETS.get(preset_name, self.PRESETS["probe"])

        amp    = min(self.MAX_AMP_UA,
                     max(self.MIN_AMP_UA,
                         preset["amp_ua"] * intensity))
        phase  = min(self.MAX_PHASE_US,
                     max(self.MIN_PHASE_US,
                         preset["phase_us"]))

        pulse  = StimPulse(
            channel   = channels[0] if channels else 27,
            phase1_us = phase,
            amp1_ua   = -amp,
            phase2_us = phase,
            amp2_ua   = amp,
        )
        burst  = StimBurst(
            channels  = [c for c in channels if 1 <= c <= 64],
            pulse     = pulse,
            count     = preset["count"],
            freq_hz   = preset["freq_hz"],
        )

        # Track safety
        charge = pulse.charge_density() * preset["count"] * len(channels)
        self._total_charge_nc += charge

        record = burst.to_dict()
        record["preset"] = preset_name
        record["desc"]   = preset["desc"]
        self._stim_history.append(record)
        self.learn(record)

        return burst

    def design_custom(self, channels: List[int],
                      amp_ua: float, phase_us: int,
                      count: int = 1, freq_hz: float = 1.0) -> StimBurst:
        """Design a custom stimulation burst."""
        amp_ua   = min(self.MAX_AMP_UA, max(self.MIN_AMP_UA, amp_ua))
        phase_us = min(self.MAX_PHASE_US, max(self.MIN_PHASE_US, phase_us))

        pulse = StimPulse(
            channel   = channels[0] if channels else 27,
            phase1_us = phase_us, amp1_ua = -amp_ua,
            phase2_us = phase_us, amp2_ua = amp_ua,
        )
        return StimBurst(channels=channels, pulse=pulse,
                         count=count, freq_hz=freq_hz)

    def cognitive_to_stim(self, cognitive_signal: str,
                          active_channels: List[int]) -> Dict:
        """
        Map a LUOKAI cognitive signal to stimulation parameters.
        Returns a dict ready to pass to NeuralBridgeCell.stimulate().
        """
        mapping = {
            "RESTING":           ("reset",      0.6),
            "ACTIVE":            ("explore",    0.8),
            "ENGAGED":           ("reinforce",  1.0),
            "FOCUSED":           ("reward",     1.0),
            "ANALYTICAL_FOCUS":  ("entrain_theta", 1.0),
            "CREATIVE_FOCUS":    ("entrain_gamma", 0.8),
            "RHYTHMIC_ACTIVE":   ("entrain_theta", 1.2),
            "SYNCHRONIZED":      ("reward",     1.2),
            "HIGH_ACTIVITY":     ("reset",      0.5),
        }
        preset_name, intensity = mapping.get(
            cognitive_signal, ("probe", 1.0)
        )
        burst = self.design_from_preset(
            preset_name,
            channels  = active_channels[:8] if active_channels else [27, 28, 35, 36],
            intensity = intensity,
        )
        return burst.to_dict()

    def list_presets(self) -> List[Dict]:
        """List all available stimulation presets."""
        return [
            {"name": k, "desc": v["desc"],
             "amp_ua": v["amp_ua"], "count": v["count"],
             "freq_hz": v["freq_hz"]}
            for k, v in self.PRESETS.items()
        ]

    def stim_history(self, n: int = 10) -> List[Dict]:
        """Get recent stimulation history."""
        return self._stim_history[-n:]

    def safety_report(self) -> Dict:
        """Report total charge delivered for safety monitoring."""
        return {
            "total_stims":       len(self._stim_history),
            "total_charge_nc":   round(self._total_charge_nc, 4),
            "safe_limit_nc":     20.0,  # nC/cm² typical safe limit
            "within_limits":     self._total_charge_nc < 10000,
        }
