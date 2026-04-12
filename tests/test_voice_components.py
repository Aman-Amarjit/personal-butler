"""Unit tests for voice components"""

import pytest
from src.voice.wake_word_detector import WakeWordDetector, WakeWordState
from src.voice.speech_to_text import SpeechToTextEngine, STTState
from src.voice.text_to_speech import TextToSpeechEngine, TTSState, ProsodySettings


class TestWakeWordDetector:
    """Test wake word detector"""

    def test_initialization(self):
        """Test detector initialization"""
        detector = WakeWordDetector(
            wake_word="Hey JARVIS",
            confidence_threshold=0.8
        )
        
        assert detector.wake_word == "hey jarvis"
        assert detector.confidence_threshold == 0.8
        assert detector.state == WakeWordState.STANDBY

    def test_custom_wake_word(self):
        """Test setting custom wake word"""
        detector = WakeWordDetector()
        detector.set_custom_wake_word("Hello Assistant")
        
        assert detector.wake_word == "hello assistant"

    def test_status(self):
        """Test detector status"""
        detector = WakeWordDetector()
        status = detector.get_status()
        
        assert "state" in status
        assert "is_monitoring" in status
        assert "wake_word" in status
        assert "cpu_usage" in status

    def test_cleanup(self):
        """Test cleanup"""
        detector = WakeWordDetector()
        detector.cleanup()
        # Should not raise exception


class TestSpeechToTextEngine:
    """Test speech-to-text engine"""

    def test_initialization(self):
        """Test STT initialization"""
        engine = SpeechToTextEngine(
            language="en",
            timeout_seconds=30
        )
        
        assert engine.language == "en"
        assert engine.timeout_seconds == 30
        assert engine.state == STTState.IDLE

    def test_language_setting(self):
        """Test language setting"""
        engine = SpeechToTextEngine()
        engine.set_language("es")
        
        assert engine.language == "es"

    def test_status(self):
        """Test engine status"""
        engine = SpeechToTextEngine()
        status = engine.get_status()
        
        assert "state" in status
        assert "is_listening" in status
        assert "language" in status
        assert "timeout_seconds" in status

    def test_cleanup(self):
        """Test cleanup"""
        engine = SpeechToTextEngine()
        engine.cleanup()
        # Should not raise exception


class TestTextToSpeechEngine:
    """Test text-to-speech engine"""

    def test_initialization(self):
        """Test TTS initialization"""
        engine = TextToSpeechEngine(
            speed=1.0,
            pitch=1.0
        )
        
        assert engine.speed == 1.0
        assert engine.pitch == 1.0
        assert engine.state == TTSState.IDLE

    def test_speed_setting(self):
        """Test speed setting"""
        engine = TextToSpeechEngine()
        engine.set_speed(1.5)
        
        assert engine.speed == 1.5

    def test_speed_bounds(self):
        """Test speed bounds"""
        engine = TextToSpeechEngine()
        
        # Test lower bound
        engine.set_speed(0.1)
        assert engine.speed == 0.5
        
        # Test upper bound
        engine.set_speed(3.0)
        assert engine.speed == 2.0

    def test_pitch_setting(self):
        """Test pitch setting"""
        engine = TextToSpeechEngine()
        engine.set_pitch(1.2)
        
        assert engine.pitch == 1.2

    def test_prosody_settings(self):
        """Test prosody settings"""
        prosody = ProsodySettings(pitch=1.2, speed=1.1, emphasis="strong")
        
        assert prosody.pitch == 1.2
        assert prosody.speed == 1.1
        assert prosody.emphasis == "strong"

    def test_status(self):
        """Test engine status"""
        engine = TextToSpeechEngine()
        status = engine.get_status()
        
        assert "state" in status
        assert "speed" in status
        assert "pitch" in status
        assert "cache_size" in status

    def test_cache_clearing(self):
        """Test cache clearing"""
        engine = TextToSpeechEngine()
        engine.audio_cache["test"] = b"audio_data"
        
        assert len(engine.audio_cache) == 1
        engine.clear_cache()
        assert len(engine.audio_cache) == 0

    def test_cleanup(self):
        """Test cleanup"""
        engine = TextToSpeechEngine()
        engine.cleanup()
        # Should not raise exception
