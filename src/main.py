"""
JARVIS AI Assistant - Main Entry Point

Starts the overlay, voice pipeline, screen vision, and game agent.
"""

import sys
import os
import argparse
import logging
import threading

# Project root on path so `src.*` imports work from anywhere
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS AI Assistant")
    parser.add_argument("--debug",    action="store_true", help="Verbose logging")
    parser.add_argument("--monitor",  type=int, default=0, help="Monitor index")
    parser.add_argument("--no-voice", action="store_true", help="Skip TTS greeting")
    parser.add_argument("--auto-play",action="store_true", help="Start autonomous game play immediately")
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    log = logging.getLogger("jarvis")
    log.info("═══════════════════════════════════════")
    log.info("  JARVIS AI Assistant  v0.1.0")
    log.info("═══════════════════════════════════════")

    # QApplication must exist before any QWidget
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    app.setApplicationVersion("0.1.0")

    try:
        from src.core.config_manager import ConfigManager
        from src.core.db_init import init_database
        from src.ui.overlay import DesktopOverlay
        from src.ui.slime_body import AnimationState

        # ── Config & DB ───────────────────────────────────────────────────
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = ConfigManager(config_dir=os.path.join(root, "config"))
        log.info(f"Environment : {config.environment}")

        init_database(os.path.join(root, "data", "jarvis.db"))
        log.info("Database    : OK")

        # ── Overlay ───────────────────────────────────────────────────────
        overlay = DesktopOverlay(monitor_id=args.monitor)
        overlay.show()
        log.info(f"Overlay     : monitor {args.monitor}")

        # ── TTS helper (shared across threads) ───────────────────────────
        tts_engine = _init_tts(config, log)

        def speak(text: str) -> None:
            log.info(f"JARVIS: {text}")
            overlay.set_animation_state(AnimationState.SPEAKING)
            if tts_engine:
                try:
                    tts_engine.say(text)
                    tts_engine.runAndWait()
                except Exception:
                    pass
            overlay.set_animation_state(AnimationState.IDLE)

        # ── Command pipeline ──────────────────────────────────────────────
        from src.core.command_interpreter import CommandInterpreter
        from src.core.command_executor import CommandExecutor, _get_screen_vision
        from src.core.response_generator import ResponseGenerator

        interpreter = CommandInterpreter()
        executor    = CommandExecutor()
        responder   = ResponseGenerator()

        def handle_text_command(text: str) -> None:
            """Process a text command end-to-end."""
            log.info(f"Command: {text}")
            overlay.set_animation_state(AnimationState.PROCESSING)
            cmd    = interpreter.parse_command(text)
            result = executor.execute(cmd)
            resp   = responder.generate_response(cmd.intent, entities=cmd.entities)
            reply  = result.output or resp.text
            speak(reply)

        # ── Screen vision (lazy, shared) ──────────────────────────────────
        # Pre-warm so first query is fast
        QTimer.singleShot(3000, lambda: _prewarm_vision(log))

        # ── Game agent ────────────────────────────────────────────────────
        from src.core.command_executor import _get_game_agent
        game_agent = _get_game_agent()
        if game_agent:
            game_agent.on_game_detected(
                lambda p: speak(f"Detected game: {p.name}. I'm ready to help.")
            )
            log.info("Game agent  : OK")

        # ── Autonomous player ─────────────────────────────────────────────
        if args.auto_play:
            from src.core.command_executor import _get_auto_player
            player = _get_auto_player()
            if player:
                player.start()
                speak("Autonomous play mode activated. I'll play for you!")
                log.info("Auto-play   : started")

        # ── Greeting ──────────────────────────────────────────────────────
        if not args.no_voice:
            QTimer.singleShot(500, lambda: speak("Hey, I'm JARVIS. I'm ready."))

        log.info("JARVIS is running.")
        log.info("  ESC in overlay to quit")
        log.info("  Say 'what do you see' to describe the screen")
        log.info("  Say 'play for me' to start autonomous game play")
        log.info("  Say 'stop playing' to stop autonomous play")

        return app.exec()

    except Exception as exc:
        logging.getLogger("jarvis").error(f"Fatal: {exc}", exc_info=True)
        return 1


# ── Helpers ────────────────────────────────────────────────────────────────

def _init_tts(config, log):
    """Initialise pyttsx3 engine, return None on failure."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", int(150 * config.get("voice.tts_speed", 1.0)))
        engine.setProperty("volume", 1.0)
        log.info("TTS         : OK")
        return engine
    except Exception as exc:
        log.warning(f"TTS unavailable: {exc}")
        return None


def _prewarm_vision(log) -> None:
    """Pre-warm the screen vision module in a background thread."""
    def _warm():
        try:
            from src.core.command_executor import _get_screen_vision
            vision = _get_screen_vision()
            if vision:
                vision._find_vision_model()
                log.info("Screen vision: ready")
        except Exception as exc:
            log.warning(f"Screen vision pre-warm failed: {exc}")
    threading.Thread(target=_warm, daemon=True).start()


if __name__ == "__main__":
    sys.exit(main())
