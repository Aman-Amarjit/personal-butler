"""
JARVIS AI Assistant - Main Entry Point
"""

import sys
import os
import argparse
import logging

# Ensure project root is on the path so `src.*` imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--monitor", type=int, default=0, help="Target monitor index")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice (UI only)")
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    logger = logging.getLogger("jarvis")
    logger.info("Starting JARVIS AI Assistant v0.1.0")

    # QApplication MUST be created before any QWidget
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    app.setApplicationVersion("0.1.0")

    try:
        from src.core.config_manager import ConfigManager
        from src.core.logger import setup_logging as setup_jarvis_logging
        from src.core.db_init import init_database
        from src.ui.overlay import DesktopOverlay
        from src.ui.visual_indicators import VisualIndicators
        from src.ui.slime_body import AnimationState

        # Load config
        config = ConfigManager(
            config_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        )
        logger.info(f"Environment: {config.environment}")

        # Init database
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "jarvis.db"
        )
        init_database(db_path)
        logger.info("Database initialized")

        # Create overlay on the requested monitor
        overlay = DesktopOverlay(monitor_id=args.monitor)
        overlay.show()
        logger.info(f"Overlay shown on monitor {args.monitor}")

        # Optionally start voice pipeline
        if not args.no_voice:
            _start_voice_pipeline(overlay, config, logger)

        logger.info("JARVIS is running. Press Escape in the overlay to quit.")
        return app.exec()

    except Exception as exc:
        logger.error(f"Fatal error: {exc}", exc_info=True)
        return 1


def _start_voice_pipeline(overlay, config, logger) -> None:
    """Start voice components in background threads (best-effort)."""
    try:
        from src.voice.text_to_speech import TextToSpeechEngine
        from src.ui.slime_body import AnimationState

        tts = TextToSpeechEngine(
            speed=config.get("voice.tts_speed", 1.0),
            pitch=config.get("voice.tts_pitch", 1.0),
        )

        def speak(text: str) -> None:
            logger.info(f"JARVIS says: {text}")
            overlay.set_animation_state(AnimationState.SPEAKING)
            tts.engine.say(text)
            tts.engine.runAndWait()
            overlay.set_animation_state(AnimationState.IDLE)

        speak("Hey, I'm JARVIS. I'm ready.")
        logger.info("Voice pipeline started")

    except Exception as exc:
        logger.warning(f"Voice pipeline unavailable (running UI-only): {exc}")


if __name__ == "__main__":
    sys.exit(main())
