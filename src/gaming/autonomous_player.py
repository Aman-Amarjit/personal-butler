"""
Autonomous Player - PANDA plays games by itself.

Runs a perception → reasoning → action loop:
  1. Capture screen
  2. Ask vision model what's happening and what to do
  3. Parse the suggestion into a concrete action
  4. Execute the action via InputController
  5. Wait, then repeat

The loop runs in a background thread and can be started/stopped at any time.
"""

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .input_controller import InputController, MacroStep
from .screen_vision import ScreenVision
from .game_detector import GameDetector, GameProfile

logger = logging.getLogger("panda.gaming.auto")


@dataclass
class AutoAction:
    """One action decided by the autonomous loop."""
    raw_suggestion: str
    parsed_key: Optional[str]
    parsed_mouse: Optional[str]
    confidence: float
    timestamp: float = field(default_factory=time.monotonic)


# ── Action parser ──────────────────────────────────────────────────────────

# Maps words the LLM might say → key names
_WORD_TO_KEY = {
    "jump":      "space",
    "crouch":    "lctrl",
    "duck":      "lctrl",
    "reload":    "r",
    "sprint":    "lshift",
    "run":       "lshift",
    "interact":  "e",
    "use":       "e",
    "attack":    "lmb",
    "shoot":     "lmb",
    "fire":      "lmb",
    "aim":       "rmb",
    "scope":     "rmb",
    "forward":   "w",
    "back":      "s",
    "backward":  "s",
    "left":      "a",
    "right":     "d",
    "inventory": "i",
    "map":       "m",
    "pause":     "escape",
    "menu":      "escape",
    "ability":   "q",
    "ultimate":  "r",
    "recall":    "b",
    "buy":       "p",
    "build":     "q",
    "dodge":     "space",
    "roll":      "space",
    "block":     "rmb",
    "parry":     "rmb",
    "heal":      "h",
    "potion":    "h",
    "sprint forward": "w",
}


def parse_action(suggestion: str) -> AutoAction:
    """
    Parse a free-text action suggestion into a concrete key/mouse action.

    Tries to find the most relevant action word in the suggestion.
    """
    lower = suggestion.lower()

    # Check for explicit key mentions like "press W" or "hold Space"
    explicit = re.search(r"\b(?:press|hold|tap|hit)\s+([a-zA-Z0-9]+)\b", lower)
    if explicit:
        key = explicit.group(1).lower()
        return AutoAction(
            raw_suggestion=suggestion,
            parsed_key=key,
            parsed_mouse=None,
            confidence=0.9,
        )

    # Check for mouse actions
    if any(w in lower for w in ("left click", "click", "shoot", "fire", "attack")):
        return AutoAction(
            raw_suggestion=suggestion,
            parsed_key=None,
            parsed_mouse="lmb",
            confidence=0.8,
        )
    if any(w in lower for w in ("right click", "aim", "scope", "ads")):
        return AutoAction(
            raw_suggestion=suggestion,
            parsed_key=None,
            parsed_mouse="rmb",
            confidence=0.8,
        )

    # Scan for known action words
    for word, key in _WORD_TO_KEY.items():
        if word in lower:
            return AutoAction(
                raw_suggestion=suggestion,
                parsed_key=key,
                parsed_mouse=None,
                confidence=0.7,
            )

    # Nothing matched — default to a small wait
    return AutoAction(
        raw_suggestion=suggestion,
        parsed_key=None,
        parsed_mouse=None,
        confidence=0.0,
    )


# ── Autonomous player ──────────────────────────────────────────────────────

class AutonomousPlayer:
    """
    Runs a perception-reasoning-action loop to play a game autonomously.

    The loop:
      every `think_interval` seconds:
        1. Capture screen
        2. Ask vision model for the best next action
        3. Parse and execute the action
        4. Log what was done
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        think_interval: float = 2.0,
        action_duration: float = 0.15,
    ):
        self.vision   = ScreenVision(ollama_url)
        self.input    = InputController()
        self.detector = GameDetector()

        self.think_interval  = think_interval   # seconds between decisions
        self.action_duration = action_duration  # how long to hold each key

        self._running  = False
        self._paused   = False
        self._thread: Optional[threading.Thread] = None
        self._lock     = threading.Lock()

        self.action_log: List[AutoAction] = []
        self._on_action: Optional[Callable[[AutoAction], None]] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the autonomous play loop."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused  = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Autonomous player started")

    def stop(self) -> None:
        """Stop the loop and release all inputs."""
        with self._lock:
            self._running = False
        self.input.release_all()
        self.input.stop_macro()
        logger.info("Autonomous player stopped")

    def pause(self) -> None:
        """Pause without stopping (keeps thread alive)."""
        with self._lock:
            self._paused = True
        self.input.release_all()
        logger.info("Autonomous player paused")

    def resume(self) -> None:
        with self._lock:
            self._paused = False
        logger.info("Autonomous player resumed")

    @property
    def is_running(self) -> bool:
        return self._running and not self._paused

    # ── Main loop ─────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue
            try:
                self._think_and_act()
            except Exception as exc:
                logger.error(f"Autonomous loop error: {exc}")
            time.sleep(self.think_interval)

    def _think_and_act(self) -> None:
        """One perception-reasoning-action cycle."""
        # Detect active game for context
        profile = self.detector.detect()
        context = f"Game: {profile.name}" if profile else ""

        # Ask vision model what to do
        suggestion = self.vision.suggest_action(context)
        logger.debug(f"AI suggestion: {suggestion}")

        # Parse into a concrete action
        action = parse_action(suggestion)
        self.action_log.append(action)
        if len(self.action_log) > 200:
            self.action_log = self.action_log[-200:]

        # Execute
        if action.parsed_mouse:
            self.input.click(action.parsed_mouse)
            logger.info(f"Auto: click {action.parsed_mouse} ({suggestion[:60]})")
        elif action.parsed_key:
            self.input.hold_for(action.parsed_key, self.action_duration)
            logger.info(f"Auto: key {action.parsed_key} ({suggestion[:60]})")
        else:
            logger.info(f"Auto: no action parsed from: {suggestion[:80]}")

        if self._on_action:
            self._on_action(action)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def on_action(self, callback: Callable[[AutoAction], None]) -> None:
        self._on_action = callback

    # ── Status ────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "running":        self._running,
            "paused":         self._paused,
            "actions_taken":  len(self.action_log),
            "last_action":    self.action_log[-1].raw_suggestion if self.action_log else None,
            "think_interval": self.think_interval,
        }

    def get_recent_actions(self, n: int = 10) -> List[str]:
        return [a.raw_suggestion for a in self.action_log[-n:]]
