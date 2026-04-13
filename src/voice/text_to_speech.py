"""
Text-to-Speech Engine

Generates natural-sounding audio responses with prosody control,
voice selection, and fallback options.
"""

import logging
import pyttsx3
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class TTSState(Enum):
    """States for text-to-speech"""
    IDLE = "idle"
    SYNTHESIZING = "synthesizing"
    PLAYING = "playing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ProsodySettings:
    """Prosody settings for speech"""
    pitch: float = 1.0  # 0.5 to 2.0
    speed: float = 1.0  # 0.5 to 2.0
    emphasis: str = "normal"  # normal, strong, reduced


class TextToSpeechEngine:
    """
    Generates speech from text with prosody control.
    
    Features:
    - pyttsx3 for local TTS (offline capable)
    - Voice selection and speed control
    - Prosody control (pitch, speed, emphasis)
    - Audio caching for common phrases
    - Fallback to edge-tts for higher quality
    """

    def __init__(
        self,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0
    ):
        """
        Initialize text-to-speech engine.

        Args:
            voice_id: Voice identifier
            speed: Speech speed (0.5-2.0)
            pitch: Speech pitch (0.5-2.0)
        """
        self.state = TTSState.IDLE
        self.speed = speed
        self.pitch = pitch
        self.voice_id = voice_id

        # Initialize pyttsx3
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", int(150 * speed))
            self.engine.setProperty("volume", 1.0)
            
            # Set voice if specified
            if voice_id:
                self.engine.setProperty("voice", voice_id)
            
            logger.info("Text-to-speech engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self.engine = None

        # Audio cache
        self.audio_cache = {}

        # Callbacks
        self.on_synthesis_complete: Optional[Callable] = None
        self.on_state_changed: Optional[Callable] = None

    def synthesize(
        self,
        text: str,
        emotion_state: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize text to audio.

        Uses pyttsx3 say()/runAndWait() for immediate playback.
        Falls back to file-based approach if direct playback fails.

        Args:
            text: Text to synthesize
            emotion_state: Emotional state for prosody

        Returns:
            Audio data bytes (from file fallback) or b"" on direct playback,
            or None if synthesis failed entirely.
        """
        if not self.engine:
            logger.error("TTS engine not initialized")
            return None

        try:
            self.state = TTSState.SYNTHESIZING
            self._notify_state_change()

            # Apply prosody based on emotion
            prosody = self._get_prosody_for_emotion(emotion_state)
            self._apply_prosody(prosody)

            # Primary: direct playback via say() + runAndWait()
            try:
                self.engine.say(text)
                self.engine.runAndWait()
                self.state = TTSState.COMPLETE
                self._notify_state_change()
                self._trigger_synthesis_complete()
                return b""  # Playback happened inline; no bytes to return
            except Exception as direct_err:
                logger.warning(f"Direct TTS playback failed ({direct_err}), trying file fallback")

            # Fallback: save to temp file and read back
            import tempfile, os
            tmp_path = os.path.join(tempfile.gettempdir(), "panda_tts_temp.wav")
            self.engine.save_to_file(text, tmp_path)
            self.engine.runAndWait()

            try:
                with open(tmp_path, "rb") as f:
                    audio_data = f.read()
            except Exception as read_err:
                logger.error(f"Could not read TTS temp file: {read_err}")
                self.state = TTSState.ERROR
                self._notify_state_change()
                return None

            # Cache and return
            cache_key = f"{text}_{emotion_state}"
            self.audio_cache[cache_key] = audio_data

            self.state = TTSState.COMPLETE
            self._notify_state_change()
            self._trigger_synthesis_complete()
            return audio_data

        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            self.state = TTSState.ERROR
            self._notify_state_change()
            return None

    def play_audio(self, audio_data: bytes) -> bool:
        """
        Play audio data.

        Args:
            audio_data: Audio data to play

        Returns:
            True if successful, False otherwise
        """
        try:
            self.state = TTSState.PLAYING
            self._notify_state_change()

            # Write to temporary file
            with open("temp_play.wav", "wb") as f:
                f.write(audio_data)

            # Play using pyttsx3 or system player
            import subprocess
            subprocess.run(["powershell", "-c", 
                          f"(New-Object Media.SoundPlayer 'temp_play.wav').PlaySync()"],
                          check=False)

            self.state = TTSState.COMPLETE
            self._notify_state_change()
            return True

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            self.state = TTSState.ERROR
            self._notify_state_change()
            return False

    def set_voice(self, voice_id: str) -> bool:
        """
        Set voice for synthesis.

        Args:
            voice_id: Voice identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.engine:
                self.engine.setProperty("voice", voice_id)
                self.voice_id = voice_id
                logger.info(f"Voice set to: {voice_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False

    def set_speed(self, speed: float) -> None:
        """
        Set speech speed.

        Args:
            speed: Speed factor (0.5-2.0)
        """
        self.speed = max(0.5, min(2.0, speed))
        if self.engine:
            self.engine.setProperty("rate", int(150 * self.speed))
        logger.info(f"Speed set to: {self.speed}")

    def set_pitch(self, pitch: float) -> None:
        """
        Set speech pitch.

        Args:
            pitch: Pitch factor (0.5-2.0)
        """
        self.pitch = max(0.5, min(2.0, pitch))
        logger.info(f"Pitch set to: {self.pitch}")

    def _get_prosody_for_emotion(self, emotion: Optional[str]) -> ProsodySettings:
        """Get prosody settings for emotion"""
        if not emotion:
            return ProsodySettings()

        emotion_map = {
            "happy": ProsodySettings(pitch=1.2, speed=1.1, emphasis="strong"),
            "sad": ProsodySettings(pitch=0.8, speed=0.9, emphasis="reduced"),
            "angry": ProsodySettings(pitch=1.3, speed=1.2, emphasis="strong"),
            "calm": ProsodySettings(pitch=0.9, speed=0.8, emphasis="reduced"),
            "neutral": ProsodySettings(pitch=1.0, speed=1.0, emphasis="normal"),
        }

        return emotion_map.get(emotion, ProsodySettings())

    def _apply_prosody(self, prosody: ProsodySettings) -> None:
        """Apply prosody settings"""
        if self.engine:
            self.engine.setProperty("rate", int(150 * prosody.speed))
            # Note: pyttsx3 has limited prosody support
            # Full prosody would require more advanced TTS

    def get_available_voices(self) -> list:
        """Get available voices"""
        try:
            if self.engine:
                voices = self.engine.getProperty("voices")
                return [v.id for v in voices]
            return []
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return []

    def _trigger_synthesis_complete(self) -> None:
        """Trigger synthesis complete callback"""
        if self.on_synthesis_complete:
            try:
                self.on_synthesis_complete()
            except Exception as e:
                logger.error(f"Error in synthesis callback: {e}")

    def _notify_state_change(self) -> None:
        """Notify state change callback"""
        if self.on_state_changed:
            try:
                self.on_state_changed(self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def get_status(self) -> dict:
        """Get engine status"""
        return {
            "state": self.state.value,
            "speed": self.speed,
            "pitch": self.pitch,
            "voice_id": self.voice_id,
            "available_voices": self.get_available_voices(),
            "cache_size": len(self.audio_cache)
        }

    def clear_cache(self) -> None:
        """Clear audio cache"""
        self.audio_cache.clear()
        logger.info("Audio cache cleared")

    def cleanup(self) -> None:
        """Clean up resources"""
        if self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                logger.error(f"Error stopping engine: {e}")

    def __del__(self):
        """Destructor"""
        self.cleanup()
