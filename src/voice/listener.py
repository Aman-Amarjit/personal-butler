"""
PANDA Voice Listener — Architecturally Remediated Pipeline

Implements all three stages from the remediation paper:

Stage 1 — Robust Hierarchical Pipeline:
  - Sentinel layer (tiny Whisper) suppressed while active command is in flight
    → fixes the "open open open" recursive trigger loop
  - Hysteresis-based VAD: onset_db > offset_db to prevent rapid state toggling
  - Configurable min_silence_duration (800 ms) and speech_pad (400 ms)
  - 200 ms pre-roll ring buffer so speech before VAD trigger is preserved
  - Adaptive silence timeout: GRACE_PERIOD before speech starts,
    SILENCE_STOP_SEC after speech ends

Stage 2 — Contextual Biasing:
  - On startup, builds Windows app manifest from registry
  - Injects top-50 app names as Whisper initial_prompt
    → increases probability that "WhatsApp" is transcribed correctly
  - Post-transcription phonetic repair via Double Metaphone + fuzzy matching

Stage 3 — Registry-Aware Execution:
  - Resolved app names passed to command executor (handled in executor)
"""

import logging
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

import numpy as np
import sounddevice as sd

log = logging.getLogger("panda.voice")

# ── Audio constants ───────────────────────────────────────────────────────────
SAMPLE_RATE  = 16000
CHANNELS     = 1
CHUNK_FRAMES = 1024          # ~64 ms per chunk

# ── Hysteresis VAD thresholds (Stage 1) ──────────────────────────────────────
# onset_db > offset_db prevents rapid toggling (hysteresis effect)
VAD_ONSET_DB  = -35.0        # dB: lowered so quieter speech is detected
VAD_OFFSET_DB = -42.0        # dB: quieter than this → speech ended (hysteresis gap = 7 dB)
WAKE_TRIGGER_DB = -38.0      # dB: minimum to bother running Whisper

# ── Timing parameters (tuned per paper recommendations) ──────────────────────
SPEECH_TIMEOUT      = 30.0   # hard cap on command recording
SILENCE_STOP_SEC    = 0.8    # min_silence_duration_ms = 800 ms (paper Table 2)
GRACE_PERIOD        = 4.0    # wait for speech to begin after wake word (increased)
SPEECH_PAD_MS       = 0.4    # speech_pad_ms = 400 ms (paper Table 2)
PRE_ROLL_SECS       = 1.5    # increased: capture more audio before VAD triggers

WAKE_CHECK_INTERVAL = 1.0    # seconds between wake-word Whisper checks
WAKE_BUFFER_SECS    = 3.0    # increased rolling buffer for wake detection


def _rms_db(audio: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    return 20.0 * np.log10(rms) if rms > 1e-10 else -100.0


class VoiceListener:
    """
    Remediated two-model voice pipeline.

    Key improvements over the original:
    - _active flag suppresses sentinel while command is in flight
      (fixes recursive "open open open" trigger)
    - Hysteresis VAD prevents rapid onset/offset toggling
    - Whisper initial_prompt injected with installed app names
    - Post-transcription phonetic repair for brand names
    """

    def __init__(
        self,
        wake_word: str = "hey panda",
        on_command: Optional[Callable[[str], None]] = None,
        on_listening: Optional[Callable[[], None]] = None,
        on_idle: Optional[Callable[[], None]] = None,
        model_size: str = "base",
        device: Optional[int] = None,
    ):
        self.wake_word    = wake_word.lower().strip()
        self.on_command   = on_command
        self.on_listening = on_listening
        self.on_idle      = on_idle
        self.cmd_model    = model_size
        self.device       = device

        self._running  = False
        self._active   = False   # True while capturing a command (sentinel suppressed)
        self._thread: Optional[threading.Thread] = None
        self._wake_model  = None
        self._cmd_model   = None
        self._audio_q: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")
        self._busy     = False

        # Whisper contextual bias prompt (Stage 2)
        self._whisper_prompt = ""
        self._build_context_prompt()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        if self._running:
            return True
        if not self._load_models():
            return False
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        log.info(f"Voice listener started (wake word: '{self.wake_word}')")
        return True

    def stop(self) -> None:
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._executor.shutdown(wait=False)
        log.info("Voice listener stopped")

    def transcribe_once(self, duration: float = 5.0) -> str:
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=CHANNELS, dtype="float32", device=self.device)
        sd.wait()
        return self._transcribe_cmd(audio.flatten())

    # ── Stage 2: Build contextual bias prompt ─────────────────────────────────

    def _build_context_prompt(self) -> None:
        """
        Build Whisper initial_prompt from installed app names.
        This biases the decoder toward proper nouns like "WhatsApp", "Spotify".
        """
        try:
            from src.core.app_discovery import get_manifest
            manifest = get_manifest()
            self._whisper_prompt = manifest.get_whisper_prompt(top_n=50)
            log.info(f"Whisper context prompt built ({manifest.app_count} apps)")
        except Exception as exc:
            log.debug(f"App manifest unavailable: {exc}")
            self._whisper_prompt = ""

    # ── Model loading ─────────────────────────────────────────────────────────

    def _load_models(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            # Use base model for BOTH wake and command — tiny is too inaccurate
            # for non-native English accents (arXiv:2309.12712 shows base is
            # significantly better for accented speech with minimal latency cost)
            log.info("Loading Whisper 'base' for wake-word detection...")
            self._wake_model = WhisperModel("base", device="cpu", compute_type="int8")
            log.info(f"Loading Whisper '{self.cmd_model}' for commands...")
            if self.cmd_model == "base":
                self._cmd_model = self._wake_model   # reuse same model
            else:
                self._cmd_model = WhisperModel(self.cmd_model, device="cpu", compute_type="int8")
            log.info("Whisper models loaded — ready to listen")
            return True
        except Exception as exc:
            log.error(f"Could not load Whisper: {exc}")
            return False

    # ── Audio callback ────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            log.debug(f"Audio status: {status}")
        self._audio_q.put(indata.copy())

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _listen_loop(self) -> None:
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32",
                blocksize=CHUNK_FRAMES, device=self.device,
                callback=self._audio_callback,
            )
            self._stream.start()
            log.info("Microphone open — listening for wake word...")
            log.info(f"  Say '{self.wake_word}' to activate PANDA")
        except Exception as exc:
            log.error(f"Could not open microphone: {exc}")
            self._running = False
            return

        max_chunks   = int(SAMPLE_RATE * WAKE_BUFFER_SECS / CHUNK_FRAMES)
        pre_roll_max = int(SAMPLE_RATE * PRE_ROLL_SECS / CHUNK_FRAMES)
        wake_buffer: List[np.ndarray] = []
        pre_roll:    List[np.ndarray] = []   # 200 ms pre-roll (Stage 1)
        last_check   = 0.0
        heard_speech = False

        while self._running:
            try:
                chunk = self._audio_q.get(timeout=1.0)
            except queue.Empty:
                continue

            flat = chunk.flatten()

            # Maintain pre-roll ring buffer
            pre_roll.append(flat)
            if len(pre_roll) > pre_roll_max:
                pre_roll.pop(0)

            wake_buffer.append(flat)
            if len(wake_buffer) > max_chunks:
                wake_buffer.pop(0)

            if _rms_db(flat) >= WAKE_TRIGGER_DB:
                heard_speech = True

            now = time.monotonic()

            # Stage 1: suppress sentinel while command is active
            if self._active or self._busy:
                continue
            if not heard_speech or now - last_check < WAKE_CHECK_INTERVAL:
                continue

            last_check   = now
            heard_speech = False
            audio_snap   = np.concatenate(wake_buffer)
            # Seed with pre-roll so speech before VAD trigger is preserved
            seed = list(pre_roll)

            self._busy = True
            self._executor.submit(self._check_wake_word, audio_snap, seed)

    def _check_wake_word(self, audio: np.ndarray, seed: List[np.ndarray]) -> None:
        """Runs in thread pool — base model for accuracy."""
        try:
            text = self._transcribe_wake(audio)
            if text:
                log.info(f"[Wake scan] heard: '{text}'")

            # Only reject obvious noise hallucinations, not real speech
            try:
                from src.core.autocorrect import is_hallucination
                if is_hallucination(text) and not _matches_wake_word(text, self.wake_word):
                    return
            except Exception:
                pass

            if text and _matches_wake_word(text, self.wake_word):
                log.info(f"Wake word detected! (heard: '{text}')")
                self._active = True

                # Extract inline command using research-backed cleaner
                try:
                    from src.core.autocorrect import clean_inline_command
                    inline_cmd = clean_inline_command(text, self.wake_word)
                except Exception:
                    inline_cmd = ""

                if inline_cmd:
                    log.info(f"Inline command: '{inline_cmd}'")
                    if self.on_listening:
                        self.on_listening()
                    if self.on_command:
                        self.on_command(inline_cmd)
                    if self.on_idle:
                        self.on_idle()
                    return

                # No inline command — wait for the user to speak
                while not self._audio_q.empty():
                    try:
                        self._audio_q.get_nowait()
                    except queue.Empty:
                        break
                self._capture_command(seed_chunks=seed)
        finally:
            self._busy   = False
            self._active = False

    # ── Command capture with hysteresis VAD ───────────────────────────────────

    def _capture_command(self, seed_chunks: Optional[List[np.ndarray]] = None) -> None:
        if self.on_listening:
            self.on_listening()

        log.info("Listening for your command...")

        # Seed with pre-roll audio (Stage 1: 200 ms pre-roll)
        speech_chunks: List[np.ndarray] = list(seed_chunks) if seed_chunks else []
        silence_start: Optional[float]  = None
        start_time    = time.monotonic()

        # Hysteresis state: track whether we're currently "in speech"
        in_speech = any(_rms_db(c) >= VAD_ONSET_DB for c in speech_chunks)
        speech_started = in_speech

        while self._running:
            elapsed = time.monotonic() - start_time
            if not speech_started and elapsed > GRACE_PERIOD:
                log.info("No speech detected after wake word — returning to standby")
                break
            if elapsed > SPEECH_TIMEOUT:
                log.info("Command capture timeout")
                break

            try:
                chunk = self._audio_q.get(timeout=0.3)
            except queue.Empty:
                continue

            flat = chunk.flatten()
            speech_chunks.append(flat)
            db = _rms_db(flat)

            # Hysteresis VAD (Stage 1):
            # onset uses VAD_ONSET_DB, offset uses VAD_OFFSET_DB (lower)
            if not in_speech and db >= VAD_ONSET_DB:
                in_speech = True
                speech_started = True
                silence_start  = None
            elif in_speech and db < VAD_OFFSET_DB:
                if silence_start is None:
                    silence_start = time.monotonic()
                elif time.monotonic() - silence_start > SILENCE_STOP_SEC:
                    # Add speech_pad_ms of extra audio before stopping
                    pad_chunks = int(SPEECH_PAD_MS * SAMPLE_RATE / CHUNK_FRAMES)
                    for _ in range(pad_chunks):
                        try:
                            extra = self._audio_q.get(timeout=0.1)
                            speech_chunks.append(extra.flatten())
                        except queue.Empty:
                            break
                    break
            elif in_speech and db >= VAD_OFFSET_DB:
                silence_start = None  # reset — still speaking

        if not speech_chunks or not speech_started:
            log.info("No speech captured after wake word")
            if self.on_idle:
                self.on_idle()
            return

        audio = np.concatenate(speech_chunks)
        log.info(f"Transcribing {len(audio)/SAMPLE_RATE:.1f}s...")
        text = self._transcribe_cmd(audio).strip()

        # Strip wake word from start
        if text:
            text = _strip_wake_word(text, self.wake_word)

        if text:
            try:
                from src.core.autocorrect import is_hallucination, autocorrect
                # Only reject clear hallucinations (noise/silence artefacts)
                if is_hallucination(text):
                    log.info(f"Hallucination discarded: '{text}'")
                    if self.on_idle:
                        self.on_idle()
                    return
                # Apply corrections
                corrected = autocorrect(text)
                # If autocorrect emptied it, it was a hallucination phrase
                if corrected:
                    if corrected != text:
                        log.info(f"Autocorrect: '{text}' → '{corrected}'")
                    text = corrected
                # else keep original — don't discard real speech just because
                # it didn't match any correction pattern
            except Exception:
                pass

            # Stage 2: registry-based app name repair
            try:
                from src.core.app_discovery import repair_app_name
                from src.core.command_interpreter import CommandInterpreter
                # Only apply registry repair if it looks like an app launch
                _launch_words = ("open", "launch", "start", "run")
                if any(w in text.lower() for w in _launch_words):
                    words = text.split()
                    # Find the app name portion (words after the verb)
                    for idx, w in enumerate(words):
                        if w.lower() in _launch_words and idx + 1 < len(words):
                            app_fragment = " ".join(words[idx+1:])
                            repaired = repair_app_name(app_fragment)
                            if repaired.lower() != app_fragment.lower():
                                text = " ".join(words[:idx+1]) + " " + repaired
                                log.info(f"App repair: '{app_fragment}' → '{repaired}'")
                            break
            except Exception:
                pass

            log.info(f"Heard command: '{text}'")
            if self.on_command:
                self.on_command(text)
        else:
            log.info("Could not understand speech — try speaking more clearly")

        if self.on_idle:
            self.on_idle()

    # ── Transcription ─────────────────────────────────────────────────────────

    def _transcribe_wake(self, audio: np.ndarray) -> str:
        """
        Wake-word check with light hallucination filtering.

        Only discards output when the model is extremely uncertain
        (avg_logprob < -2.0) — this catches pure noise/silence while
        keeping real speech. Threshold tuned conservatively because
        false rejects (missing wake word) are worse than false accepts
        at this stage.
        """
        if self._wake_model is None:
            return ""
        try:
            segs, _ = self._wake_model.transcribe(
                audio, language="en", beam_size=1, vad_filter=False,
            )
            seg_list = list(segs)
            if not seg_list:
                return ""
            avg_lp = sum(s.avg_logprob for s in seg_list) / len(seg_list)
            # Only reject if extremely uncertain (pure noise)
            if avg_lp < -2.0:
                log.debug(f"Wake scan: low confidence ({avg_lp:.2f}), skipping")
                return ""
            text = " ".join(s.text for s in seg_list).strip()
            return text
        except Exception as exc:
            log.debug(f"Wake transcription error: {exc}")
            return ""

    def _transcribe_cmd(self, audio: np.ndarray) -> str:
        """
        Command transcription with contextual biasing (Stage 2).

        - Uses base model for accuracy
        - Injects app names as initial_prompt to bias toward proper nouns
        - Falls back to tiny model for very short audio (<1.5 s)
          per arXiv:2309.12712 sample-dependent model selection
        """
        duration = len(audio) / SAMPLE_RATE
        model = self._wake_model if duration < 1.5 else self._cmd_model
        if model is None:
            return ""
        try:
            kwargs: dict = dict(language="en", beam_size=3, vad_filter=False)
            # Inject contextual bias prompt (Stage 2)
            if self._whisper_prompt and duration >= 1.5:
                kwargs["initial_prompt"] = self._whisper_prompt
            segs, _ = model.transcribe(audio, **kwargs)
            return " ".join(s.text for s in segs).strip()
        except Exception as exc:
            log.error(f"Command transcription error: {exc}")
            return ""


# ── Wake word matching ────────────────────────────────────────────────────────

def _matches_wake_word(text: str, wake_word: str) -> bool:
    import re
    text_clean = re.sub(r"[^\w\s]", "", text.lower())
    text_words = text_clean.split()
    wake_words = wake_word.lower().split()
    last = wake_words[-1]   # e.g. "panda"

    # Hard reject: last wake word must be at least 4 chars and not a common word
    COMMON = {"yes","no","the","a","i","ok","hi","hey","and","or","but",
              "so","is","it","in","on","at","to","do","go","be","me","my","we",
              "see","say","day","way","may","pay","say","lay","ray","bay"}
    if len(last) < 4 or last in COMMON:
        return False

    # 1. Full phrase exact match (most reliable)
    if wake_word in text_clean:
        return True

    # 2. All words of wake phrase present as whole words
    if all(w in text_words for w in wake_words):
        return True

    # 3. Last word as exact whole word match
    if last in text_words:
        return True

    # 4. Last word as substring of a longer word (catches "pandas", "pander")
    #    BUT only if the word is long enough to avoid false matches
    for w in text_words:
        if len(w) >= len(last) and last in w:
            return True

    # 5. Edit distance — STRICT: only allow distance=1 AND word must be
    #    at least 80% the length of the wake word to avoid "see"→"panda" matches
    for w in text_words:
        if (len(w) >= max(4, len(last) - 1) and
                abs(len(w) - len(last)) <= 1 and
                _edit_distance(w, last) <= 1):
            return True

    return False


def _strip_wake_word(text: str, wake_word: str) -> str:
    import re
    for pat in [
        re.compile(r"^\s*" + re.escape(wake_word) + r"\s*[,.]?\s*", re.I),
        re.compile(r"^\s*" + re.escape(wake_word.split()[-1]) + r"\s*[,.]?\s*", re.I),
    ]:
        result = pat.sub("", text).strip()
        if result and result != text:
            return result
    return text


def _edit_distance(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 99
    if a == b:
        return 0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[j] = min(dp[j]+1, dp[j-1]+1, prev[j-1]+cost)
    return dp[n]
