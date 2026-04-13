"""
Speech-to-Text Pipeline

Converts voice input to text using faster-whisper with streaming support,
confidence scoring, and resource-aware fallback.
"""

import logging
import threading
import time
import queue
from typing import Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_FRAMES = 1024
SILENCE_DB = -35.0
SPEECH_TIMEOUT = 30.0
SILENCE_STOP_SEC = 1.2


def _rms_db(audio: np.ndarray) -> float:
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-10:
        return -100.0
    return 20.0 * np.log10(rms)


class STTState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    duration_seconds: float


class SpeechToTextEngine:
    """
    Converts speech to text using faster-whisper.

    Features:
    - faster-whisper (local, no API key)
    - VAD-filtered transcription
    - Confidence score from avg log-prob
    - Language selection
    - Graceful fallback if model unavailable
    """

    def __init__(
        self,
        language: str = "en",
        timeout_seconds: float = SPEECH_TIMEOUT,
        confidence_threshold: float = 0.5,
        model_size: str = "tiny",
    ):
        self.language = language
        self.timeout_seconds = timeout_seconds
        self.confidence_threshold = confidence_threshold
        self.model_size = model_size

        self.state = STTState.IDLE
        self.is_listening = False
        self._whisper = None
        self._audio_q: queue.Queue = queue.Queue()
        self._stream = None
        self._listen_thread: Optional[threading.Thread] = None

        self.on_transcription_complete: Optional[Callable[[TranscriptionResult], None]] = None
        self.on_state_changed: Optional[Callable[[STTState], None]] = None

        self._load_model()

    # ── Model loading ─────────────────────────────────────────────────────

    def _load_model(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper '{self.model_size}' model for STT...")
            self._whisper = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
            logger.info("Whisper STT model loaded")
            return True
        except Exception as exc:
            logger.warning(f"faster-whisper not available: {exc}. STT disabled.")
            return False

    # ── Public API ────────────────────────────────────────────────────────

    def start_listening(self) -> bool:
        if self.is_listening:
            return False
        if self._whisper is None:
            logger.error("Whisper model not loaded — cannot listen")
            return False

        self.is_listening = True
        self.state = STTState.LISTENING
        self._notify_state_change()
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        logger.info(f"STT listening started (timeout {self.timeout_seconds}s)")
        return True

    def cancel_listening(self) -> None:
        self.is_listening = False
        logger.info("STT listening cancelled")

    def transcribe_audio(self, audio: np.ndarray) -> Optional[TranscriptionResult]:
        """Transcribe a numpy float32 audio array directly."""
        if self._whisper is None:
            return None
        return self._run_whisper(audio)

    def set_language(self, language_code: str) -> None:
        self.language = language_code

    # ── Internal ──────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug(f"Audio status: {status}")
        self._audio_q.put(indata.copy())

    def _listen_loop(self) -> None:
        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=CHUNK_FRAMES,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            logger.error(f"Could not open microphone for STT: {exc}")
            self.state = STTState.ERROR
            self._notify_state_change()
            self.is_listening = False
            return

        chunks = []
        silence_start: Optional[float] = None
        start = time.monotonic()

        while self.is_listening:
            if time.monotonic() - start > self.timeout_seconds:
                logger.info("STT timeout")
                break
            try:
                chunk = self._audio_q.get(timeout=0.5)
            except queue.Empty:
                continue

            flat = chunk.flatten()
            chunks.append(flat)
            db = _rms_db(flat)

            if db < SILENCE_DB:
                if silence_start is None:
                    silence_start = time.monotonic()
                elif time.monotonic() - silence_start > SILENCE_STOP_SEC:
                    break
            else:
                silence_start = None

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass

        if not chunks:
            self.state = STTState.ERROR
            self._notify_state_change()
            return

        audio = np.concatenate(chunks)
        self.state = STTState.PROCESSING
        self._notify_state_change()

        result = self._run_whisper(audio)
        self.state = STTState.COMPLETE
        self._notify_state_change()
        if result and self.on_transcription_complete:
            try:
                self.on_transcription_complete(result)
            except Exception as exc:
                logger.error(f"Transcription callback error: {exc}")

    def _run_whisper(self, audio: np.ndarray) -> Optional[TranscriptionResult]:
        if self._whisper is None:
            return None
        try:
            segments, info = self._whisper.transcribe(
                audio,
                language=self.language if self.language != "auto" else None,
                beam_size=1,
                vad_filter=True,
            )
            seg_list = list(segments)
            text = " ".join(s.text for s in seg_list).strip()
            # avg_logprob is per-segment; use mean as confidence proxy
            if seg_list:
                avg_lp = sum(s.avg_logprob for s in seg_list) / len(seg_list)
                confidence = min(1.0, max(0.0, 1.0 + avg_lp))  # logprob ∈ (-∞, 0]
            else:
                confidence = 0.0
            duration = float(audio.shape[0]) / SAMPLE_RATE
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=info.language,
                duration_seconds=duration,
            )
        except Exception as exc:
            logger.error(f"Whisper transcription error: {exc}")
            return None

    def _notify_state_change(self) -> None:
        if self.on_state_changed:
            try:
                self.on_state_changed(self.state)
            except Exception:
                pass

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "is_listening": self.is_listening,
            "language": self.language,
            "model_size": self.model_size,
            "model_loaded": self._whisper is not None,
            "timeout_seconds": self.timeout_seconds,
            "confidence_threshold": self.confidence_threshold,
        }

    def cleanup(self) -> None:
        self.cancel_listening()

    def __del__(self):
        self.cleanup()
