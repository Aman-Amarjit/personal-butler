"""
Game Agent - Orchestrates game automation via voice commands.

Listens for game-specific voice commands, maps them to macros,
and executes them through the InputController.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .input_controller import InputController, MacroStep
from .game_detector import GameDetector, GameProfile

logger = logging.getLogger("panda.gaming.agent")


@dataclass
class GameSession:
    """Active game session state."""
    profile: GameProfile
    start_time: float = field(default_factory=time.monotonic)
    commands_executed: int = 0
    active: bool = True


class GameAgent:
    """
    Bridges voice commands to game input.

    Usage:
        agent = GameAgent()
        agent.start()
        agent.handle_voice_command("jump")   # executes the jump macro
        agent.stop()
    """

    def __init__(self):
        self.input  = InputController()
        self.detector = GameDetector()
        self.session: Optional[GameSession] = None
        self._running = False
        self._detect_thread: Optional[threading.Thread] = None
        self._on_game_detected: Optional[Callable[[GameProfile], None]] = None
        self._on_command_executed: Optional[Callable[[str], None]] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self, auto_detect: bool = True) -> None:
        """Start the game agent."""
        self._running = True
        if auto_detect:
            self._detect_thread = threading.Thread(
                target=self._detection_loop, daemon=True
            )
            self._detect_thread.start()
        logger.info("Game agent started")

    def stop(self) -> None:
        """Stop the game agent and release all inputs."""
        self._running = False
        self.input.release_all()
        self.input.stop_macro()
        if self.session:
            self.session.active = False
        logger.info("Game agent stopped")

    # ── Detection loop ────────────────────────────────────────────────────

    def _detection_loop(self) -> None:
        """Periodically detect the active game."""
        last_game = None
        while self._running:
            profile = self.detector.detect()
            name = profile.name if profile else None
            if name != last_game:
                if profile:
                    self._on_new_game(profile)
                else:
                    self.session = None
                last_game = name
            time.sleep(3.0)

    def _on_new_game(self, profile: GameProfile) -> None:
        self.session = GameSession(profile=profile)
        logger.info(f"Game session started: {profile.name} ({profile.genre})")
        if self._on_game_detected:
            self._on_game_detected(profile)

    # ── Voice command handling ────────────────────────────────────────────

    def handle_voice_command(self, text: str) -> Optional[str]:
        """
        Process a voice command string and execute the matching macro.

        Args:
            text: Transcribed voice command (e.g. "jump", "reload")

        Returns:
            Human-readable result string, or None if not handled.
        """
        text_lower = text.lower().strip()

        # Determine active profile
        profile = self.session.profile if self.session else None

        # Try to match against active profile first, then all profiles
        result = self._try_execute(text_lower, profile)
        if result:
            return result

        # Fallback: scan all profiles
        for p in self.detector.profiles:
            result = self._try_execute(text_lower, p)
            if result:
                return result

        # Generic movement commands always work
        return self._handle_generic(text_lower)

    def _try_execute(self, text: str, profile: Optional[GameProfile]) -> Optional[str]:
        if profile is None:
            return None
        for phrase, macro_name in profile.voice_commands.items():
            if phrase in text:
                return self._execute_macro(macro_name, profile)
        return None

    def _execute_macro(self, macro_name: str, profile: GameProfile) -> str:
        steps_raw = profile.macros.get(macro_name, [])
        if not steps_raw:
            return f"No macro defined for '{macro_name}'"

        steps = [
            MacroStep(
                action=s.get("action", "press"),
                key=s.get("key", ""),
                duration=s.get("duration", 0.0),
                x=s.get("x", 0),
                y=s.get("y", 0),
            )
            for s in steps_raw
        ]

        self.input.run_macro(steps, blocking=False)

        if self.session:
            self.session.commands_executed += 1

        msg = f"Executed '{macro_name}' in {profile.name}"
        logger.info(msg)
        if self._on_command_executed:
            self._on_command_executed(macro_name)
        return msg

    def _handle_generic(self, text: str) -> Optional[str]:
        """Handle universal commands that work in any game."""
        generic = {
            "stop":          lambda: self.input.release_all(),
            "escape":        lambda: self.input.press("escape"),
            "pause":         lambda: self.input.press("escape"),
            "screenshot":    lambda: self.input.press("f12"),
            "fullscreen":    lambda: self.input.press("f11"),
            "tab":           lambda: self.input.press("tab"),
        }
        for phrase, action in generic.items():
            if phrase in text:
                action()
                return f"Executed generic command: {phrase}"
        return None

    # ── Manual control ────────────────────────────────────────────────────

    def force_profile(self, game_name: str) -> bool:
        """Manually set the active game profile by name."""
        profile = self.detector.get_profile(game_name)
        if profile:
            self._on_new_game(profile)
            return True
        return False

    def execute_key(self, key: str, hold: bool = False,
                    duration: float = 0.0) -> str:
        """Directly press or hold a key."""
        if hold and duration > 0:
            threading.Thread(
                target=self.input.hold_for,
                args=(key, duration),
                daemon=True,
            ).start()
            return f"Holding {key} for {duration}s"
        elif hold:
            self.input.hold(key)
            return f"Holding {key}"
        else:
            self.input.press(key)
            return f"Pressed {key}"

    def release_key(self, key: str) -> str:
        self.input.release(key)
        return f"Released {key}"

    def release_all(self) -> str:
        self.input.release_all()
        return "Released all keys"

    # ── Callbacks ─────────────────────────────────────────────────────────

    def on_game_detected(self, callback: Callable[[GameProfile], None]) -> None:
        self._on_game_detected = callback

    def on_command_executed(self, callback: Callable[[str], None]) -> None:
        self._on_command_executed = callback

    # ── Status ────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "active_game": self.session.profile.name if self.session else None,
            "commands_executed": self.session.commands_executed if self.session else 0,
            "supported_games": self.detector.list_supported_games(),
        }
