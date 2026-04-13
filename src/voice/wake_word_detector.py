"""
Wake Word Detection Engine

Detects activation phrase with minimal CPU overhead using
faster-whisper for local, privacy-preserving detection.
"""

import logging
import threading
import time
import queue
from typing import Callable, Optional
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_FRAMES = 1024
SILENCE_DB = -40.0          # dB — only transcribe when audio is loud enough
WAKE_BUFFER_SECS = 3.0      # rolling window for wake-word check


def _rms_db(audio: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-10:
        return -100.0
    return 20.0 * np.log10(rms)


class WakeWordState(Enum):
    STANDBY = "standby"
    LISTENING = "listening"
    DETECTED = "detected"
    ERROR = "error"


class WakeWordDetector:
    """
    Detects wake word using faster-whisper on a rolling audio buffer.

    Features:
    - Local model (faster-whisper tiny — ~75 MB)
    - Continuous monitoring in standby
    - Custom wake word support
    - CPU usage monitoring (<5% target)
    - Audio device detection and fallback
    """

    def __init__(
        self,
        wake_word: str = "Hey PANDA",
        model_path: Optional[str] = None,   # kept for API compat, unused
        confidence_threshold: float = 0.8,
        model_size: str = "tiny",
    ):
        self.wake_word = wake_word.lower()
        self.confidence_threshold = confidence_threshold
        self.model_size = model_size

        self.state = WakeWordState.STANDBY
        self.is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._whisper = None
        self._audio_q: queue.Queue = queue.Queue()
        self._stream = None

        self.on_wake_word_detected: Optional[Callable[[], None]] = None
        self.on_state_changed: Optional[Callable[[WakeWordState], None]] = None

        self._load_model()

    # ── Model ─────────────────────────────────────────────────────────────

    def _load_model(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper '{self.model_size}' for wake-word detection...")
            self._whisper = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
            logger.info("Wake-word Whisper model loaded")
            return True
        except Exception as exc:
            logger.warning(f"faster-whisper unavailable for wake-word: {exc}")
            return False

    # ── Public API ────────────────────────────────────────────────────────

    def start_monitoring(self) -> bool:
        if self.is_monitoring:
            return False
        if self._whisper is None:
            logger.error("Whisper model not loaded — wake-word detection disabled")
            return False

        self.is_monitoring = True
        self.state = WakeWordState.STANDBY
        self._notify_state_change()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"Wake-word monitoring started (phrase: '{self.wake_word}')")
        return True

    def stop_monitoring(self) -> None:
        self.is_monitoring = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        logger.info("Wake-word monitoring stopped")

    def set_custom_wake_word(self, wake_word: str) -> None:
        self.wake_word = wake_word.lower()
        logger.info(f"Wake word changed to: '{wake_word}'")

    def get_cpu_usage(self) -> float:
        try:
            import psutil
            return psutil.Process().cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    @property
    def is_listening(self) -> bool:
        """True when actively listening (not in standby)."""
        return self.state == WakeWordState.LISTENING

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "is_monitoring": self.is_monitoring,
            "wake_word": self.wake_word,
            "cpu_usage": self.get_cpu_usage(),
            "confidence_threshold": self.confidence_threshold,
            "model_loaded": self._whisper is not None,
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug(f"Audio status: {status}")
        self._audio_q.put(indata.copy())

    def _monitor_loop(self) -> None:
        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_FRAMES,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Microphone open — listening for wake word...")
        except Exception as exc:
            logger.error(f"Could not open microphone: {exc}")
            self.state = WakeWordState.ERROR
            self._notify_state_change()
            self.is_monitoring = False
            return

        wake_buf: list = []
        max_chunks = int(SAMPLE_RATE * WAKE_BUFFER_SECS / CHUNK_FRAMES)

        while self.is_monitoring:
            try:
                chunk = self._audio_q.get(timeout=1.0)
            except queue.Empty:
                continue

            flat = chunk.flatten()
            wake_buf.append(flat)
            if len(wake_buf) > max_chunks:
                wake_buf.pop(0)

            # Only run Whisper when there's actual audio
            if _rms_db(flat) < SILENCE_DB:
                continue

            audio_3s = np.concatenate(wake_buf)
            if self._detect_wake_word(audio_3s):
                logger.info("Wake word detected!")
                self.state = WakeWordState.DETECTED
                self._notify_state_change()
                wake_buf.clear()
                if self.on_wake_word_detected:
                    try:
                        self.on_wake_word_detected()
                    except Exception as exc:
                        logger.error(f"Wake-word callback error: {exc}")
                # Return to standby after callback
                self.state = WakeWordState.STANDBY
                self._notify_state_change()

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass

    def _detect_wake_word(self, audio: np.ndarray) -> bool:
        """Run Whisper on the rolling buffer and check for wake phrase."""
        if self._whisper is None:
            return False
        try:
            segments, _ = self._whisper.transcribe(
                audio,
                language="en",
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(s.text for s in segments).lower().strip()
            if not text:
                return False
            # Direct match
            if self.wake_word in text:
                return True
            # Fuzzy: last word of wake phrase present (catches mishearings)
            last_word = self.wake_word.split()[-1]
            return last_word in text
        except Exception as exc:
            logger.debug(f"Wake-word transcription error: {exc}")
            return False

    def _notify_state_change(self) -> None:
        if self.on_state_changed:
            try:
                self.on_state_changed(self.state)
            except Exception:
                pass

    def cleanup(self) -> None:
        self.stop_monitoring()

    def __del__(self):
        self.cleanup()
