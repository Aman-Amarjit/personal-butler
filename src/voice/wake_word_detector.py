"""
Wake Word Detection Engine

Detects activation phrase with minimal CPU overhead using
Vosk or Silero models for local, privacy-preserving detection.
"""

import logging
import threading
import pyaudio
from typing import Callable, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class WakeWordState(Enum):
    """States for wake word detection"""
    STANDBY = "standby"
    LISTENING = "listening"
    DETECTED = "detected"
    ERROR = "error"


class WakeWordDetector:
    """
    Detects wake word with minimal CPU overhead.
    
    Features:
    - Local model (Vosk or Silero)
    - Continuous monitoring in standby
    - Custom wake word support
    - CPU usage monitoring (<5% target)
    - Audio device detection and fallback
    """

    def __init__(
        self,
        wake_word: str = "Hey JARVIS",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.8
    ):
        """
        Initialize wake word detector.

        Args:
            wake_word: Phrase to detect
            model_path: Path to Vosk model
            confidence_threshold: Detection confidence threshold
        """
        self.wake_word = wake_word.lower()
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold

        self.state = WakeWordState.STANDBY
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Audio
        self.audio_interface = None
        self.stream = None
        self.chunk_size = 4096
        self.sample_rate = 16000

        # Callbacks
        self.on_wake_word_detected: Optional[Callable] = None
        self.on_state_changed: Optional[Callable] = None

        # Initialize audio
        self._initialize_audio()

    def _initialize_audio(self) -> bool:
        """
        Initialize audio interface and detect devices.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.audio_interface = pyaudio.PyAudio()
            
            # List available devices
            device_count = self.audio_interface.get_device_count()
            logger.info(f"Found {device_count} audio devices")

            for i in range(device_count):
                info = self.audio_interface.get_device_info_by_index(i)
                logger.debug(f"Device {i}: {info['name']}")

            logger.info("Audio interface initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            return False

    def start_monitoring(self) -> bool:
        """
        Start continuous wake word monitoring.

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return False

        try:
            self.is_monitoring = True
            self.state = WakeWordState.STANDBY
            self._notify_state_change()

            # Start monitoring in background thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()

            logger.info("Wake word monitoring started")
            return True
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.is_monitoring = False
            return False

    def stop_monitoring(self) -> None:
        """Stop wake word monitoring"""
        self.is_monitoring = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                logger.error(f"Error closing stream: {e}")

        logger.info("Wake word monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop running in background thread"""
        try:
            # Open audio stream
            self.stream = self.audio_interface.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            logger.info("Audio stream opened for monitoring")

            while self.is_monitoring:
                try:
                    # Read audio chunk
                    audio_data = self.stream.read(
                        self.chunk_size,
                        exception_on_overflow=False
                    )

                    # Process audio for wake word
                    if self._detect_wake_word(audio_data):
                        self.state = WakeWordState.DETECTED
                        self._notify_state_change()
                        self._trigger_wake_word_detected()

                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    self.state = WakeWordState.ERROR
                    self._notify_state_change()

        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            self.state = WakeWordState.ERROR
            self._notify_state_change()
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()

    def _detect_wake_word(self, audio_data: bytes) -> bool:
        """
        Detect wake word in audio data.

        Args:
            audio_data: Audio chunk data

        Returns:
            True if wake word detected, False otherwise
        """
        try:
            # Placeholder for actual wake word detection
            # In production, would use Vosk or Silero model
            
            # For now, return False (no detection)
            # This will be implemented with actual model
            return False
        except Exception as e:
            logger.error(f"Error detecting wake word: {e}")
            return False

    def _trigger_wake_word_detected(self) -> None:
        """Trigger wake word detected callback"""
        if self.on_wake_word_detected:
            try:
                self.on_wake_word_detected()
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")

    def _notify_state_change(self) -> None:
        """Notify state change callback"""
        if self.on_state_changed:
            try:
                self.on_state_changed(self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def set_custom_wake_word(self, wake_word: str) -> None:
        """
        Set custom wake word.

        Args:
            wake_word: New wake word phrase
        """
        self.wake_word = wake_word.lower()
        logger.info(f"Wake word changed to: {wake_word}")

    def get_cpu_usage(self) -> float:
        """
        Get CPU usage of wake word detection.

        Returns:
            CPU usage percentage
        """
        try:
            import psutil
            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 0.0

    def get_status(self) -> dict:
        """
        Get detector status.

        Returns:
            Status dictionary
        """
        return {
            "state": self.state.value,
            "is_monitoring": self.is_monitoring,
            "wake_word": self.wake_word,
            "cpu_usage": self.get_cpu_usage(),
            "confidence_threshold": self.confidence_threshold
        }

    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop_monitoring()
        
        if self.audio_interface:
            try:
                self.audio_interface.terminate()
            except Exception as e:
                logger.error(f"Error terminating audio interface: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
