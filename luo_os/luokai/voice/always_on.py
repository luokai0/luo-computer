#!/usr/bin/env python3
"""
LUOKAI Always-On Voice System
24/7 listening — no button needed.
Pipeline: VAD → Wake Word → STT → LUOKAI Brain → TTS → repeat

Uses:
  - WebRTC VAD for voice activity detection
  - "Luo" or "LUOKAI" as wake word (phonetic match)
  - Whisper (local) or SpeechRecognition for STT
  - pyttsx3 / edge-tts / Coqui for TTS
  - Runs as background daemon thread
"""
import threading, time, queue, re, json, subprocess, sys, os
import urllib.request
from pathlib import Path

class AlwaysOnVoice:
    """24/7 voice I/O daemon for LuoOS."""

    WAKE_WORDS = ["luo", "luokai", "hey luo", "ok luo", "yo luo"]
    STOP_WORDS = ["stop listening", "quiet", "mute yourself", "shut up luo"]

    def __init__(self, brain_callback, sample_rate=16000, chunk=1024):
        self.brain_callback = brain_callback  # fn(text) -> str
        self.sample_rate    = sample_rate
        self.chunk          = chunk
        self._running       = False
        self._muted         = False
        self._speaking      = False
        self._audio_q       = queue.Queue()
        self._state         = "idle"   # idle / listening_wake / capturing_cmd / speaking
        self._tts_lock      = threading.Lock()
        self.wake_count     = 0
        self.cmd_count      = 0
        self._print         = self._make_printer()

    def _make_printer(self):
        cols = {"idle":"⬜","listening_wake":"👂","capturing_cmd":"🎙️","speaking":"🔊"}
        def p(msg, level="info"):
            state_icon = cols.get(self._state, "❓")
            print(f"\r[{state_icon} VOICE] {msg}", flush=True)
        return p

    # ── TTS ─────────────────────────────────────────────────────────
    def speak(self, text: str):
        """Speak text. Non-blocking."""
        if not text or self._muted: return
        with self._tts_lock:
            self._state    = "speaking"
            self._speaking = True
            self._tts(text)
            self._speaking = False
            self._state    = "listening_wake"

    def _tts(self, text: str):
        """Try TTS engines in order of quality."""
        text = text[:400].strip()
        # 1. edge-tts (high quality, needs internet)
        try:
            import asyncio, edge_tts, tempfile, os, platform
            async def _do():
                tmp = tempfile.mktemp(suffix=".mp3")
                comm = edge_tts.Communicate(text, "en-US-GuyNeural")
                await comm.save(tmp)
                import shutil
                if shutil.which("mpg123"):   subprocess.run(["mpg123","-q",tmp],check=False)
                elif shutil.which("mpv"):    subprocess.run(["mpv","--no-video",tmp],check=False)
                elif shutil.which("afplay"): subprocess.run(["afplay",tmp],check=False)
                else:                        subprocess.run(["start",tmp],shell=True,check=False)
                os.unlink(tmp)
            asyncio.run(_do())
            return
        except Exception: pass

        # 2. pyttsx3 (offline, all platforms)
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate", 185)
            eng.say(text)
            eng.runAndWait()
            return
        except Exception: pass

        # 3. Platform native
        import platform
        plat = platform.system()
        try:
            if plat == "Darwin":   subprocess.run(["say", "-r", "185", text])
            elif plat == "Windows":
                ps = f'(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                subprocess.run(["powershell","-Command",ps], capture_output=True)
            else:
                subprocess.run(["espeak", "-s", "175", text], capture_output=True)
        except Exception as e:
            print(f"[TTS ERROR] {e}")

    # ── STT ─────────────────────────────────────────────────────────
    def _stt_from_audio(self, audio) -> str:
        """Convert audio to text using best available engine."""
        # 1. Whisper (best quality, fully offline)
        try:
            import whisper
            import numpy as np
            if not hasattr(self, "_whisper_model"):
                self._print("Loading Whisper tiny model...")
                self._whisper_model = whisper.load_model("tiny")
            audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            result   = self._whisper_model.transcribe(audio_np, language="en", fp16=False)
            return result.get("text","").strip()
        except Exception: pass

        # 2. SpeechRecognition (Google / Sphinx)
        try:
            import speech_recognition as sr
            import io, wave, tempfile
            rec  = sr.Recognizer()
            tmp  = tempfile.mktemp(suffix=".wav")
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio)
            with sr.AudioFile(tmp) as src:
                aud = rec.record(src)
            os.unlink(tmp)
            try:    return rec.recognize_google(aud)
            except: return rec.recognize_sphinx(aud)
        except Exception: pass

        return ""

    # ── VAD — Voice Activity Detection ───────────────────────────────
    def _has_voice(self, chunk_bytes: bytes) -> bool:
        """Simple energy-based VAD (works without webrtcvad)."""
        import struct, math
        try:
            samples = struct.unpack(f"{len(chunk_bytes)//2}h", chunk_bytes)
            rms     = math.sqrt(sum(s*s for s in samples) / len(samples))
            return rms > 800  # threshold for speech vs silence
        except Exception:
            return False

    def _is_wake_word(self, text: str) -> bool:
        """Check if text contains wake word."""
        tl = text.lower().strip()
        return any(w in tl for w in self.WAKE_WORDS)

    def _is_stop_word(self, text: str) -> bool:
        tl = text.lower()
        return any(s in tl for s in self.STOP_WORDS)

    def _strip_wake_word(self, text: str) -> str:
        """Remove wake word from beginning of command."""
        t = text.lower().strip()
        for w in sorted(self.WAKE_WORDS, key=len, reverse=True):
            if t.startswith(w):
                t = t[len(w):].strip().lstrip(",").strip()
                break
        return t or text

    # ── MAIN LISTEN LOOP ─────────────────────────────────────────────
    def start(self):
        """Start 24/7 listening in background thread."""
        self._running = True
        t = threading.Thread(target=self._listen_loop, daemon=True, name="LuoVoice")
        t.start()
        self._print(f"Always-on voice started. Say any of: {self.WAKE_WORDS}")
        return t

    def stop(self):
        self._running = False
        self._print("Voice daemon stopped.")

    def mute(self):
        self._muted = True
        self._print("Muted.")

    def unmute(self):
        self._muted = False
        self._print("Unmuted.")

    def _listen_loop(self):
        try:
            import pyaudio
        except ImportError:
            print("[VOICE] pyaudio not installed. Run: pip install pyaudio")
            return

        pa      = pyaudio.PyAudio()
        stream  = pa.open(
            rate            = self.sample_rate,
            channels        = 1,
            format          = pyaudio.paInt16,
            input           = True,
            frames_per_buffer = self.chunk,
        )

        SILENCE_LIMIT  = int(self.sample_rate / self.chunk * 1.5)  # 1.5s silence = end of speech
        WAKE_SCAN_LEN  = int(self.sample_rate / self.chunk * 3)    # 3s scan window for wake word
        CMD_MAX_LEN    = int(self.sample_rate / self.chunk * 12)   # max 12s command

        self._state = "listening_wake"
        self._print("Waiting for wake word...")

        scan_buf   = b""
        scan_count = 0

        while self._running:
            try:
                raw = stream.read(self.chunk, exception_on_overflow=False)
            except Exception:
                continue

            if self._speaking:
                continue  # don't listen while speaking

            # ── PHASE 1: Scan for wake word in rolling 3s window
            if self._state == "listening_wake":
                scan_buf   += raw
                scan_count += 1
                if scan_count >= WAKE_SCAN_LEN:
                    # Process scan buffer
                    text = self._stt_from_audio(scan_buf)
                    scan_buf   = b""
                    scan_count = 0
                    if text and self._is_wake_word(text):
                        self.wake_count += 1
                        self._print(f"Wake word detected! [{text}]")
                        # Immediate ack beep
                        self.speak("Yes?")
                        self._state = "capturing_cmd"
                        cmd_buf     = b""
                        silence_cnt = 0
                        voice_detected = False
                    elif text:
                        self._print(f"Heard (no wake): {text[:40]!r}")

            # ── PHASE 2: Capture command after wake word
            elif self._state == "capturing_cmd":
                cmd_buf += raw
                has_v    = self._has_voice(raw)
                if has_v:
                    voice_detected = True
                    silence_cnt    = 0
                else:
                    silence_cnt += 1

                too_long  = len(cmd_buf) // (self.chunk * 2) >= CMD_MAX_LEN
                timed_out = voice_detected and silence_cnt >= SILENCE_LIMIT

                if timed_out or too_long:
                    self._state = "listening_wake"
                    if voice_detected and len(cmd_buf) > self.chunk * 4:
                        text = self._stt_from_audio(cmd_buf)
                        cmd_buf = b""
                        if text:
                            # Strip wake word if user said it again
                            if self._is_wake_word(text):
                                text = self._strip_wake_word(text)
                            if self._is_stop_word(text):
                                self.mute()
                                self.speak("Muted. Say 'Luo unmute' to turn back on.")
                            elif text.strip():
                                self._print(f"Command: {text!r}")
                                self.cmd_count += 1
                                # Call brain
                                threading.Thread(
                                    target=self._process_command,
                                    args=(text,),
                                    daemon=True
                                ).start()
                    else:
                        cmd_buf = b""
                    scan_buf   = b""
                    scan_count = 0

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def _process_command(self, text: str):
        """Process command through brain and speak response."""
        try:
            response = self.brain_callback(text)
            if response:
                # Trim long responses for speech
                spoken = response[:300]
                # Remove markdown
                spoken = re.sub(r'\*\*(.+?)\*\*', r'\1', spoken)
                spoken = re.sub(r'#+\s+', '', spoken)
                spoken = re.sub(r'[`*_]', '', spoken)
                spoken = re.sub(r'http\S+', 'link', spoken)
                self.speak(spoken)
        except Exception as e:
            self.speak(f"Error: {e}")

    def status(self) -> dict:
        return {
            "running":     self._running,
            "muted":       self._muted,
            "state":       self._state,
            "wake_count":  self.wake_count,
            "cmd_count":   self.cmd_count,
            "wake_words":  self.WAKE_WORDS,
        }


# ── Standalone test ──────────────────────────────────────────────────
if __name__ == "__main__":
    def dummy_brain(text):
        return f"You said: {text}. I am LUOKAI, your AI in LuoOS."

    voice = AlwaysOnVoice(dummy_brain)
    voice.start()
    print("Press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
            s = voice.status()
            print(f"\r[{s['state']}] wakes={s['wake_count']} cmds={s['cmd_count']}  ", end="", flush=True)
    except KeyboardInterrupt:
        voice.stop()
