"""
PANDA AI Assistant - Main Entry Point
"""

import sys
import os
import argparse
import logging
import threading
import queue

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
    parser = argparse.ArgumentParser(description="PANDA AI Assistant")
    parser.add_argument("--debug",     action="store_true", help="Verbose logging")
    parser.add_argument("--monitor",   type=int, default=0, help="Monitor index")
    parser.add_argument("--no-voice",  action="store_true", help="Skip voice listener")
    parser.add_argument("--auto-play", action="store_true", help="Start autonomous game play")
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    log = logging.getLogger("panda")
    log.info("═══════════════════════════════════════")
    log.info("  PANDA AI Assistant  v0.1.0")
    log.info("═══════════════════════════════════════")

    app = QApplication(sys.argv)
    app.setApplicationName("PANDA")
    app.setApplicationVersion("0.1.0")

    try:
        from src.core.config_manager import ConfigManager
        from src.core.db_init import init_database
        from src.ui.overlay import DesktopOverlay
        from src.ui.slime_body import AnimationState

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = ConfigManager(config_dir=os.path.join(root, "config"))
        log.info(f"Environment : {config.environment}")

        init_database(os.path.join(root, "data", "panda.db"))
        log.info("Database    : OK")

        overlay = DesktopOverlay(monitor_id=args.monitor)
        overlay.show()
        log.info(f"Overlay     : monitor {args.monitor}")

        # ── TTS: dedicated background thread ─────────────────────────────
        # pyttsx3.runAndWait() blocks — it MUST NOT run on the Qt main thread
        # or the event loop freezes and the UI stops updating.
        # Solution: a dedicated TTS thread that blocks on a queue.
        _speak_q: queue.Queue = queue.Queue()
        _tts_rate = int(150 * config.get("voice.tts_speed", 1.0))

        def _tts_worker() -> None:
            """Dedicated TTS thread — owns the pyttsx3 engine exclusively."""
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", _tts_rate)
                engine.setProperty("volume", 1.0)
                log.info("TTS thread  : OK")
            except Exception as exc:
                log.warning(f"TTS unavailable: {exc}")
                engine = None

            while True:
                try:
                    item = _speak_q.get(timeout=1.0)
                except queue.Empty:
                    continue
                if item is None:          # shutdown signal
                    break
                text, is_singing = item
                log.info(f"PANDA speaking: '{text[:60]}'")
                if engine:
                    try:
                        if is_singing:
                            engine.setProperty("rate", 160)
                        engine.say(text)
                        engine.runAndWait()
                        if is_singing:
                            engine.setProperty("rate", _tts_rate)
                        log.info("PANDA speaking: done")
                    except Exception as exc:
                        log.warning(f"TTS error: {exc} — re-initialising")
                        try:
                            engine = pyttsx3.init()
                            engine.setProperty("rate", _tts_rate)
                            engine.setProperty("volume", 1.0)
                        except Exception:
                            engine = None
                _speak_q.task_done()

        tts_thread = threading.Thread(target=_tts_worker, daemon=True, name="tts")
        tts_thread.start()
        log.info("TTS         : OK")

        # State-reset queue: TTS thread puts (state, delay_ms) here;
        # a Qt timer on the main thread drains it safely.
        _state_reset_q: queue.Queue = queue.Queue()

        def _drain_state_resets() -> None:
            """Called by QTimer on the main thread — safe for Qt."""
            while not _state_reset_q.empty():
                try:
                    state_after, delay_ms = _state_reset_q.get_nowait()
                except queue.Empty:
                    break
                # Use singleShot here — we ARE on the main thread now
                QTimer.singleShot(delay_ms, lambda s=state_after: overlay.set_animation_state(s))

        state_timer = QTimer(app)
        state_timer.timeout.connect(_drain_state_resets)
        state_timer.start(150)

        def speak(text: str,
                  state_after: AnimationState = AnimationState.IDLE,
                  singing: bool = False) -> None:
            """Queue text for TTS. Safe to call from any thread."""
            overlay.set_animation_state(
                AnimationState.DANCING if singing else AnimationState.SPEAKING
            )
            overlay.set_last_text(text)
            _speak_q.put((text, singing))
            # Schedule state reset via the state-reset queue (thread-safe)
            delay_ms = max(500, len(text.split()) * 400)
            _state_reset_q.put((state_after, delay_ms))

        # ── Command pipeline ──────────────────────────────────────────────
        from src.core.command_interpreter import CommandInterpreter
        from src.core.command_executor import CommandExecutor
        from src.core.response_generator import ResponseGenerator
        from src.core.ollama_integration import OllamaIntegration
        from src.memory import EpisodicMemory, LocalRAG

        interpreter = CommandInterpreter()
        executor    = CommandExecutor()
        responder   = ResponseGenerator()

        db_path  = os.path.join(root, "data", "panda.db")
        episodic = EpisodicMemory(db_path=db_path)
        rag      = LocalRAG(db_path=db_path)
        ollama   = OllamaIntegration(
            host=config.get("ollama.host", "http://localhost"),
            port=config.get("ollama.port", 11434),
        )

        import uuid
        _session_id = str(uuid.uuid4())[:8]

        def handle_text_command(text: str) -> None:
            """Process a command. Called from the voice background thread."""
            # Sanitise: strip leading punctuation/garbage from inline commands
            import re
            text = re.sub(r"^[\s?.!,]+", "", text).strip()
            if not text or len(text) < 2:
                return

            log.info(f"Command: {text}")
            overlay.set_animation_state(AnimationState.PROCESSING)
            overlay.set_last_text(text)

            episodic.store(text, role="user", session_id=_session_id)
            rag.learn_from_conversation(text, "")

            try:
                cmd    = interpreter.parse_command(text)
                result = executor.execute(cmd)

                from src.core.command_interpreter import CommandIntent
                if cmd.intent == CommandIntent.INFORMATION_RETRIEVAL and not result.output:
                    if ollama.verify_running():
                        # Use first available model, not hardcoded mistral:7b
                        models = ollama.list_models()
                        if models:
                            ollama.current_model = models[0]
                        rag_answer = rag.query(text, ollama)
                        reply = rag_answer
                    else:
                        resp  = responder.generate_response(cmd.intent, entities=cmd.entities)
                        reply = str(resp)
                elif cmd.intent == CommandIntent.SING:
                    resp  = responder.generate_response(cmd.intent, entities=cmd.entities)
                    reply = result.output or str(resp)
                    episodic.store(reply, role="assistant", session_id=_session_id)
                    speak(reply, state_after=AnimationState.IDLE, singing=True)
                    return
                else:
                    resp  = responder.generate_response(cmd.intent, entities=cmd.entities)
                    reply = result.output or str(resp)

            except Exception as exc:
                log.error(f"Command pipeline error: {exc}", exc_info=True)
                reply = "Sorry, I ran into an error processing that."

            episodic.store(reply, role="assistant", session_id=_session_id)
            speak(reply, state_after=AnimationState.IDLE)

        # ── Screen vision pre-warm ────────────────────────────────────────
        QTimer.singleShot(3000, lambda: _prewarm_vision(log))

        # ── Game agent ────────────────────────────────────────────────────
        from src.core.command_executor import _get_game_agent
        game_agent = _get_game_agent()
        if game_agent:
            game_agent.on_game_detected(
                lambda p: speak(f"Detected game: {p.name}. I'm ready to help.")
            )
            log.info("Game agent  : OK")

        # ── Voice listener ────────────────────────────────────────────────
        if not args.no_voice:
            _start_listener(overlay, config, log, handle_text_command, speak)
        else:
            log.info("Voice listener disabled (--no-voice)")
            speak("Hey, I'm PANDA. I'm ready.")

        log.info("PANDA is running. Say 'Hey PANDA' to activate.")
        ret = app.exec()
        _speak_q.put(None)   # shutdown TTS thread
        return ret

    except Exception as exc:
        logging.getLogger("panda").error(f"Fatal: {exc}", exc_info=True)
        return 1


# ── Helpers ───────────────────────────────────────────────────────────────────

def _start_listener(overlay, config, log, handle_text_command, speak) -> None:
    from src.ui.slime_body import AnimationState

    def on_listening():
        overlay.set_animation_state(AnimationState.LISTENING)

    def on_idle():
        overlay.set_animation_state(AnimationState.IDLE)

    wake_word  = config.get("voice.wake_word", "Hey PANDA")
    model_size = config.get("voice.whisper_model", "base")

    try:
        from src.voice.listener import VoiceListener
        listener = VoiceListener(
            wake_word=wake_word,
            on_command=handle_text_command,
            on_listening=on_listening,
            on_idle=on_idle,
            model_size=model_size,
        )
        ok = listener.start()
        if ok:
            log.info(f"Voice listener : OK  (wake word: '{wake_word}', model: {model_size})")
            speak(f"Hey, I'm PANDA. Say {wake_word} to activate me.")
        else:
            log.warning("Voice listener failed to start.")
            speak("Hey, I'm PANDA. Voice input is unavailable right now.")
    except ImportError as exc:
        log.warning(f"Voice listener unavailable: {exc}")
        speak("Hey, I'm PANDA. Install faster-whisper to enable voice.")
    except Exception as exc:
        log.error(f"Voice listener error: {exc}", exc_info=True)
        speak("Hey, I'm PANDA. I had trouble starting the microphone.")


def _prewarm_vision(log) -> None:
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
