#!/usr/bin/env python3
"""
luokai/cells/neural/bridge.py
==============================
NeuralBridgeCell — connects biological neuron activity (Cortical Labs CL1)
to LUOKAI's AI cell network.

The CL1 MEA has 64 channels (electrodes), each sampled at 25,000 Hz.
Action potentials (spikes) are detected and processed here.

Real hardware: requires `pip install cl` and a connected CL1 device.
Simulation mode: runs without hardware for development and testing.
"""
import time
import json
import threading
import collections
from typing import Any, Dict, List, Optional, Callable, Tuple
from pathlib import Path
from ..base import BaseCell


# ═══════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════

class SpikePattern:
    """
    Represents a detected pattern from neural spike activity.
    LUOKAI maps spike patterns to cognitive states and intents.
    """
    def __init__(self, channels: List[int], timestamps: List[float],
                 rate_hz: float, pattern_type: str = "unknown"):
        self.channels    = channels       # which electrodes fired
        self.timestamps  = timestamps     # when they fired
        self.rate_hz     = rate_hz        # spikes per second
        self.pattern_type = pattern_type  # "burst", "sync", "sparse", "silent"
        self.created_at  = time.time()

    def to_dict(self) -> Dict:
        return {
            "channels":     self.channels,
            "count":        len(self.timestamps),
            "rate_hz":      round(self.rate_hz, 2),
            "pattern":      self.pattern_type,
            "channel_count": len(set(self.channels)),
        }

    def __repr__(self):
        return (f"SpikePattern({self.pattern_type}, "
                f"{len(self.channels)} spikes, "
                f"{self.rate_hz:.1f}Hz)")


class ChannelState:
    """Tracks state of a single MEA channel over time."""
    def __init__(self, channel_id: int):
        self.id          = channel_id
        self.spike_times = collections.deque(maxlen=1000)
        self.last_spike  = None
        self.total_spikes = 0

    def record_spike(self, timestamp: float):
        self.spike_times.append(timestamp)
        self.last_spike = timestamp
        self.total_spikes += 1

    def rate_hz(self, window_seconds: float = 1.0) -> float:
        """Calculate spike rate in last window_seconds."""
        if not self.spike_times:
            return 0.0
        now = time.time()
        recent = [t for t in self.spike_times if now - t <= window_seconds]
        return len(recent) / window_seconds

    def is_active(self, window_seconds: float = 0.5) -> bool:
        return self.rate_hz(window_seconds) > 0.5


# ═══════════════════════════════════════════════════════════════════
# NEURAL BRIDGE CELL
# ═══════════════════════════════════════════════════════════════════

class NeuralBridgeCell(BaseCell):
    """
    Core cell that bridges CL1 biological neurons to LUOKAI.

    In real mode: connects to CL1 hardware via `import cl`
    In sim mode:  generates synthetic spike patterns for development

    Spike → Pattern → LUOKAI cognitive signal
    LUOKAI decision → Stimulus design → Electrode stimulation
    """
    category = "neural"

    # MEA layout: 64 channels in 8×8 grid (channels 1-64)
    MEA_CHANNELS     = 64
    SAMPLE_RATE_HZ   = 25_000   # 25kHz, one frame every 40µs
    SPIKE_THRESHOLD_UV = 50.0   # µV threshold for spike detection

    def __init__(self, name: str = "neural_bridge",
                 sim_mode: bool = True,
                 ticks_per_second: int = 1000):
        super().__init__(name)
        self.sim_mode         = sim_mode
        self.ticks_per_second = ticks_per_second
        self._running         = False
        self._thread: Optional[threading.Thread] = None
        self._spike_log: collections.deque = collections.deque(maxlen=50_000)
        self._channels: Dict[int, ChannelState] = {
            i: ChannelState(i) for i in range(1, self.MEA_CHANNELS + 1)
        }
        self._callbacks: List[Callable[[SpikePattern], None]] = []
        self._stim_queue: collections.deque = collections.deque(maxlen=1000)  # thread-safe deque
        self._cl_neurons  = None   # CL1 hardware connection
        self._stats = {
            "total_spikes": 0,
            "total_stims":  0,
            "patterns_detected": 0,
            "loop_ticks": 0,
        }
        print(f"[NeuralBridgeCell] Init — mode={'SIM' if sim_mode else 'CL1 HARDWARE'}")

    # ── Hardware connection ──────────────────────────────────────
    def connect_hardware(self) -> bool:
        """Try to connect to real CL1 hardware."""
        try:
            import cl
            self._cl_neurons = cl.open().__enter__()
            self.sim_mode = False
            print("[NeuralBridgeCell] ✅ Connected to CL1 hardware")
            return True
        except ImportError:
            print("[NeuralBridgeCell] CL library not installed — staying in sim mode")
            print("[NeuralBridgeCell]   Install: pip install cl")
        except Exception as e:
            print(f"[NeuralBridgeCell] CL1 hardware not available: {e}")
        return False

    # ── Loop control ─────────────────────────────────────────────
    def start(self, background: bool = True):
        """Start the neural processing loop."""
        if self._running:
            return
        self._running = True
        if background:
            self._thread = threading.Thread(
                target=self._run_loop, daemon=True, name="NeuralBridge"
            )
            self._thread.start()
            print(f"[NeuralBridgeCell] Started in background ({self.ticks_per_second}Hz)")
        else:
            self._run_loop()

    def stop(self):
        """Stop the neural processing loop."""
        self._running = False
        if self._cl_neurons:
            try:
                self._cl_neurons.__exit__(None, None, None)
            except Exception:
                pass
            self._cl_neurons = None
        print("[NeuralBridgeCell] Stopped")

    def _run_loop(self):
        """Main neural processing loop."""
        if self.sim_mode:
            self._run_sim_loop()
        else:
            self._run_cl_loop()

    def _run_cl_loop(self):
        """Run against real CL1 hardware using the Loop API."""
        try:
            import cl
            with cl.open() as neurons:
                self._cl_neurons = neurons
                for tick in neurons.loop(
                    ticks_per_second=self.ticks_per_second,
                    ignore_jitter=True
                ):
                    if not self._running:
                        break
                    self._process_tick_cl(tick, neurons)
                    self._stats["loop_ticks"] += 1
        except Exception as e:
            print(f"[NeuralBridgeCell] CL loop error: {e}")
            print("[NeuralBridgeCell] Falling back to sim mode")
            self.sim_mode = True
            self._run_sim_loop()

    def _process_tick_cl(self, tick: Any, neurons: Any):
        """Process one CL1 tick — read spikes, dispatch stims."""
        # Read incoming spikes
        spikes = tick.analysis.spikes
        for spike in spikes:
            ch  = int(spike.channel)
            ts  = float(spike.timestamp)
            self._record_spike(ch, ts)

        # Detect patterns every 100 ticks
        if self._stats["loop_ticks"] % 100 == 0:
            pattern = self._detect_pattern()
            if pattern:
                self._dispatch_pattern(pattern)

        # Send queued stimulations
        while self._stim_queue:
            stim = self._stim_queue.popleft()
            try:
                import cl
                channels  = stim.get("channels", [27])
                design    = stim.get("design", {})
                phase1_us = design.get("phase1_us", 180)
                amp1_ua   = design.get("amp1_ua", -1.5)
                phase2_us = design.get("phase2_us", 180)
                amp2_ua   = design.get("amp2_ua", 1.5)
                bursts    = stim.get("bursts", 1)
                burst_hz  = stim.get("burst_hz", 1)

                ch_set = cl.ChannelSet(*channels)
                sd     = cl.StimDesign(phase1_us, amp1_ua, phase2_us, amp2_ua)

                if bursts > 1:
                    neurons.stim(ch_set, sd, cl.BurstDesign(bursts, burst_hz))
                else:
                    neurons.stim(ch_set, sd)

                self._stats["total_stims"] += 1
            except Exception as e:
                print(f"[NeuralBridgeCell] Stim error: {e}")

    def _run_sim_loop(self):
        """Simulation mode — synthetic spikes for development."""
        import random, math

        tick = 0
        interval = 1.0 / self.ticks_per_second

        while self._running:
            t_start = time.time()
            tick += 1

            # Simulate realistic neural activity
            # Resting rate ~5-15 Hz per active electrode
            # Bursts of 50-200 Hz for 20-50ms every 500-2000ms
            for ch in range(1, self.MEA_CHANNELS + 1):
                state = self._channels[ch]
                base_rate = 8.0  # Hz

                # Add burst dynamics
                burst_phase = math.sin(tick / (self.ticks_per_second * 1.5) + ch * 0.3)
                if burst_phase > 0.85:
                    rate = base_rate * 12  # burst
                else:
                    rate = base_rate

                prob = rate / self.ticks_per_second
                if random.random() < prob:
                    self._record_spike(ch, time.time())

            # Detect patterns every 200ms
            if tick % max(1, self.ticks_per_second // 5) == 0:
                pattern = self._detect_pattern()
                if pattern and self._callbacks:
                    self._dispatch_pattern(pattern)

            self._stats["loop_ticks"] += 1

            # Precise sleep to maintain tick rate
            elapsed = time.time() - t_start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ── Core logic ───────────────────────────────────────────────
    def _record_spike(self, channel: int, timestamp: float):
        """Record a spike on a channel."""
        if 1 <= channel <= self.MEA_CHANNELS:
            self._channels[channel].record_spike(timestamp)
            self._spike_log.append((channel, timestamp))
            self._stats["total_spikes"] += 1

    def _detect_pattern(self, window_seconds: float = 0.2) -> Optional[SpikePattern]:
        """Detect the current spike pattern from recent activity."""
        now = time.time()
        recent_spikes = [
            (ch, ts) for ch, ts in self._spike_log
            if now - ts <= window_seconds
        ]

        if not recent_spikes:
            return None

        channels  = [ch for ch, _ in recent_spikes]
        timestamps = [ts for _, ts in recent_spikes]
        rate_hz   = len(recent_spikes) / window_seconds
        active_ch = len(set(channels))

        # Classify pattern
        if rate_hz > 200:
            ptype = "burst"          # high-frequency burst
        elif rate_hz > 50 and active_ch > 20:
            ptype = "synchronous"    # many channels firing together
        elif rate_hz < 5:
            ptype = "sparse"         # low activity
        elif active_ch < 5:
            ptype = "focal"          # activity concentrated in few channels
        else:
            ptype = "distributed"    # normal distributed activity

        self._stats["patterns_detected"] += 1
        return SpikePattern(channels, timestamps, rate_hz, ptype)

    def _dispatch_pattern(self, pattern: SpikePattern):
        """Send pattern to all registered callbacks (LUOKAI brain cells)."""
        self.learn(pattern.to_dict())  # store in cell memory
        for cb in self._callbacks:
            try:
                cb(pattern)
            except Exception as e:
                print(f"[NeuralBridgeCell] Callback error: {e}")

    # ── Public API ───────────────────────────────────────────────
    def on_pattern(self, callback: Callable[[SpikePattern], None]):
        """Register a callback for pattern events."""
        self._callbacks.append(callback)

    def stimulate(self, channels: List[int],
                  amp_ua: float = 1.5,
                  phase_us: int = 180,
                  bursts: int = 1,
                  burst_hz: float = 50.0):
        """
        Queue a stimulation for the given channels.

        channels  — list of electrode numbers (1-64)
        amp_ua    — amplitude in microamperes (1.0-2.0 typical)
        phase_us  — pulse phase duration in microseconds (160-320 typical)
        bursts    — number of pulses in burst (1 = single pulse)
        burst_hz  — frequency of burst pulses
        """
        # Clamp to safe values
        amp_ua   = max(0.5, min(3.0, amp_ua))
        phase_us = max(80, min(480, phase_us))
        channels = [c for c in channels if 1 <= c <= self.MEA_CHANNELS]

        if not channels:
            return

        stim = {
            "channels":  channels,
            "design": {
                "phase1_us": phase_us,
                "amp1_ua":   -abs(amp_ua),   # cathodic first
                "phase2_us": phase_us,
                "amp2_ua":   abs(amp_ua),    # then anodic
            },
            "bursts":    bursts,
            "burst_hz":  burst_hz,
            "queued_at": time.time(),
        }
        self._stim_queue.append(stim)  # deque.append is thread-safe

    def get_channel_rates(self) -> Dict[int, float]:
        """Get spike rates for all channels (Hz)."""
        return {ch: state.rate_hz() for ch, state in self._channels.items()}

    def get_active_channels(self, threshold_hz: float = 1.0) -> List[int]:
        """Get list of channels with spike rate above threshold."""
        return [ch for ch, state in self._channels.items()
                if state.rate_hz() >= threshold_hz]

    def get_latest_pattern(self) -> Optional[SpikePattern]:
        """Get the most recently detected spike pattern."""
        return self._detect_pattern()

    def process(self, signal: Any) -> Any:
        """BaseCell process — interpret signal as a stimulation command."""
        super().process(signal)
        if isinstance(signal, dict):
            channels = signal.get("channels", [27])
            amp      = signal.get("amp_ua", 1.5)
            self.stimulate(channels, amp_ua=amp)
        return signal

    def status(self) -> Dict:
        """Get full status of the neural bridge."""
        base = super().status()
        active = self.get_active_channels()
        return {
            **base,
            "mode":           "sim" if self.sim_mode else "cl1_hardware",
            "running":        self._running,
            "active_channels": len(active),
            "total_spikes":   self._stats["total_spikes"],
            "total_stims":    self._stats["total_stims"],
            "patterns":       self._stats["patterns_detected"],
            "loop_ticks":     self._stats["loop_ticks"],
            "stim_queued":    len(self._stim_queue),
        }


# ═══════════════════════════════════════════════════════════════════
# NEURAL ENGINE — orchestrates the bridge + LUOKAI integration
# ═══════════════════════════════════════════════════════════════════

class NeuralEngine:
    """
    Manages the full biological↔AI loop:

    CL1 Neurons → NeuralBridgeCell → SpikeInterpreter
        → LUOKAI Brain (cognition)
        → StimulusDesigner
        → CL1 Neurons (feedback)
    """

    def __init__(self, sim_mode: bool = True,
                 ticks_per_second: int = 100,
                 auto_start: bool = False):
        self.bridge = NeuralBridgeCell(
            sim_mode=sim_mode,
            ticks_per_second=ticks_per_second
        )
        self._pattern_history: List[Dict] = []
        self._cognitive_state = "idle"
        self._luokai_callback: Optional[Callable] = None

        # Register our pattern handler
        self.bridge.on_pattern(self._on_pattern)

        if auto_start:
            self.start()

        print(f"[NeuralEngine] Ready — {'SIM' if sim_mode else 'HARDWARE'} mode")

    def _on_pattern(self, pattern: SpikePattern):
        """Handle incoming spike pattern from the MEA."""
        self._pattern_history.append(pattern.to_dict())
        if len(self._pattern_history) > 500:
            self._pattern_history = self._pattern_history[-400:]

        # Map pattern to cognitive state
        self._cognitive_state = self._pattern_to_state(pattern)

        # Forward to LUOKAI if connected
        if self._luokai_callback:
            try:
                self._luokai_callback(self._cognitive_state, pattern)
            except Exception as e:
                print(f"[NeuralEngine] LUOKAI callback error: {e}")

    def _pattern_to_state(self, pattern: SpikePattern) -> str:
        """Map a spike pattern to a LUOKAI cognitive state."""
        p = pattern.pattern_type
        r = pattern.rate_hz

        if p == "burst":
            return "excited"           # high activity = excitement/alertness
        elif p == "synchronous" and r > 100:
            return "focused"           # sync high activity = concentration
        elif p == "synchronous":
            return "processing"        # moderate sync = processing
        elif p == "sparse":
            return "resting"           # low activity = rest
        elif p == "focal":
            return "localised"         # few channels = localised computation
        else:
            return "active"            # normal distributed activity

    def connect_luokai(self, callback: Callable):
        """Connect LUOKAI brain to receive neural states."""
        self._luokai_callback = callback
        print("[NeuralEngine] Connected to LUOKAI brain")

    def start(self, try_hardware: bool = True):
        """Start the neural engine."""
        if try_hardware and self.bridge.sim_mode:
            self.bridge.connect_hardware()
        self.bridge.start(background=True)

    def stop(self):
        """Stop the neural engine."""
        self.bridge.stop()

    def stimulate_response(self, cognitive_signal: str,
                           intensity: float = 1.0):
        """
        Convert a LUOKAI cognitive signal into electrode stimulation.

        cognitive_signal — "reward", "correct", "error", "explore", "reinforce"
        intensity        — 0.0 to 1.0
        """
        active = self.bridge.get_active_channels()
        if not active:
            active = [27, 28, 35, 36]  # default centre channels

        stim_map = {
            "reward":    {"channels": active[:4], "amp_ua": 1.5 * intensity, "bursts": 5, "burst_hz": 50},
            "correct":   {"channels": active[:2], "amp_ua": 1.2 * intensity, "bursts": 3, "burst_hz": 30},
            "error":     {"channels": active[-2:], "amp_ua": 0.8 * intensity, "bursts": 1, "burst_hz": 1},
            "explore":   {"channels": active[:8], "amp_ua": 1.0 * intensity, "bursts": 2, "burst_hz": 20},
            "reinforce": {"channels": active[:4], "amp_ua": 1.8 * intensity, "bursts": 8, "burst_hz": 100},
        }

        stim = stim_map.get(cognitive_signal,
                             {"channels": [27], "amp_ua": 1.0, "bursts": 1, "burst_hz": 1})

        self.bridge.stimulate(
            channels  = stim["channels"],
            amp_ua    = stim["amp_ua"],
            bursts    = stim["bursts"],
            burst_hz  = stim["burst_hz"],
        )

    def get_cognitive_state(self) -> str:
        """Get current cognitive state derived from neural activity."""
        pattern = self.bridge.get_latest_pattern()
        if pattern:
            return self._pattern_to_state(pattern)
        return "idle"

    def get_recent_patterns(self, n: int = 10) -> List[Dict]:
        """Get the last n detected patterns."""
        return self._pattern_history[-n:]

    def status(self) -> Dict:
        """Full engine status."""
        return {
            "cognitive_state":  self._cognitive_state,
            "bridge":           self.bridge.status(),
            "patterns_logged":  len(self._pattern_history),
            "luokai_connected": bool(self._luokai_callback),
        }
