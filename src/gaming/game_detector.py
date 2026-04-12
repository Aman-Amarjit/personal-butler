"""
Game Detector - Detects running games and returns their profiles.

Scans running processes for known game executables and window titles,
then loads the matching control profile.
"""

import ctypes
import ctypes.wintypes
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("jarvis.gaming.detector")


@dataclass
class GameProfile:
    """Control profile for a specific game."""
    name: str
    exe_patterns: List[str]          # regex patterns for process names
    window_patterns: List[str]       # regex patterns for window titles
    genre: str = "unknown"           # fps, rpg, rts, moba, platformer, etc.
    # Voice command → macro name mapping
    voice_commands: Dict[str, str] = field(default_factory=dict)
    # Macro name → list of (action, key, duration) tuples
    macros: Dict[str, List[dict]] = field(default_factory=dict)


# ── Built-in game profiles ─────────────────────────────────────────────────

BUILTIN_PROFILES: List[GameProfile] = [

    GameProfile(
        name="Minecraft",
        exe_patterns=[r"javaw\.exe", r"minecraft.*\.exe"],
        window_patterns=[r"minecraft", r"java.*minecraft"],
        genre="sandbox",
        voice_commands={
            "jump":         "jump",
            "attack":       "attack",
            "use":          "use",
            "sneak":        "sneak",
            "sprint":       "sprint",
            "inventory":    "inventory",
            "drop":         "drop",
            "walk forward": "walk_forward",
            "stop":         "stop_moving",
            "hotbar 1":     "hotbar_1",
            "hotbar 2":     "hotbar_2",
            "hotbar 3":     "hotbar_3",
        },
        macros={
            "jump":         [{"action": "press",  "key": "space"}],
            "attack":       [{"action": "click",  "key": "lmb"}],
            "use":          [{"action": "click",  "key": "rmb"}],
            "sneak":        [{"action": "hold",   "key": "lshift"}],
            "sprint":       [{"action": "hold",   "key": "lctrl"}],
            "inventory":    [{"action": "press",  "key": "e"}],
            "drop":         [{"action": "press",  "key": "q"}],
            "walk_forward": [{"action": "hold",   "key": "w"}],
            "stop_moving":  [{"action": "release","key": "w"},
                             {"action": "release","key": "a"},
                             {"action": "release","key": "s"},
                             {"action": "release","key": "d"}],
            "hotbar_1":     [{"action": "press",  "key": "1"}],
            "hotbar_2":     [{"action": "press",  "key": "2"}],
            "hotbar_3":     [{"action": "press",  "key": "3"}],
        },
    ),

    GameProfile(
        name="Fortnite",
        exe_patterns=[r"fortniteclient.*\.exe"],
        window_patterns=[r"fortnite"],
        genre="battle_royale",
        voice_commands={
            "jump":         "jump",
            "crouch":       "crouch",
            "reload":       "reload",
            "build wall":   "build_wall",
            "build floor":  "build_floor",
            "build ramp":   "build_ramp",
            "edit":         "edit",
            "harvest":      "harvest",
            "sprint":       "sprint",
            "stop":         "stop_moving",
        },
        macros={
            "jump":         [{"action": "press",  "key": "space"}],
            "crouch":       [{"action": "press",  "key": "lctrl"}],
            "reload":       [{"action": "press",  "key": "r"}],
            "build_wall":   [{"action": "press",  "key": "q"}],
            "build_floor":  [{"action": "press",  "key": "f"}],
            "build_ramp":   [{"action": "press",  "key": "v"}],
            "edit":         [{"action": "press",  "key": "g"}],
            "harvest":      [{"action": "hold",   "key": "lmb", "duration": 0.5}],
            "sprint":       [{"action": "hold",   "key": "lshift"}],
            "stop_moving":  [{"action": "release","key": "w"},
                             {"action": "release","key": "lshift"}],
        },
    ),

    GameProfile(
        name="Counter-Strike",
        exe_patterns=[r"cs2\.exe", r"csgo\.exe"],
        window_patterns=[r"counter.strike", r"cs2", r"csgo"],
        genre="fps",
        voice_commands={
            "jump":         "jump",
            "crouch":       "crouch",
            "reload":       "reload",
            "buy":          "buy_menu",
            "bomb":         "drop_bomb",
            "flash":        "throw_flash",
            "smoke":        "throw_smoke",
            "spray":        "spray",
            "stop":         "stop_moving",
        },
        macros={
            "jump":         [{"action": "press",  "key": "space"}],
            "crouch":       [{"action": "hold",   "key": "lctrl"}],
            "reload":       [{"action": "press",  "key": "r"}],
            "buy_menu":     [{"action": "press",  "key": "b"}],
            "drop_bomb":    [{"action": "press",  "key": "g"}],
            "throw_flash":  [{"action": "press",  "key": "4"}],
            "throw_smoke":  [{"action": "press",  "key": "3"}],
            "spray":        [{"action": "hold",   "key": "lmb", "duration": 1.0}],
            "stop_moving":  [{"action": "release","key": "w"},
                             {"action": "release","key": "a"},
                             {"action": "release","key": "s"},
                             {"action": "release","key": "d"}],
        },
    ),

    GameProfile(
        name="League of Legends",
        exe_patterns=[r"league.*client.*\.exe", r"leagueoflegends\.exe"],
        window_patterns=[r"league of legends"],
        genre="moba",
        voice_commands={
            "attack move":  "attack_move",
            "recall":       "recall",
            "ability 1":    "ability_q",
            "ability 2":    "ability_w",
            "ability 3":    "ability_e",
            "ultimate":     "ability_r",
            "flash":        "summoner_d",
            "ignite":       "summoner_f",
            "shop":         "shop",
            "score":        "score",
            "stop":         "stop",
        },
        macros={
            "attack_move":  [{"action": "press",  "key": "a"}],
            "recall":       [{"action": "press",  "key": "b"}],
            "ability_q":    [{"action": "press",  "key": "q"}],
            "ability_w":    [{"action": "press",  "key": "w"}],
            "ability_e":    [{"action": "press",  "key": "e"}],
            "ability_r":    [{"action": "press",  "key": "r"}],
            "summoner_d":   [{"action": "press",  "key": "d"}],
            "summoner_f":   [{"action": "press",  "key": "f"}],
            "shop":         [{"action": "press",  "key": "p"}],
            "score":        [{"action": "press",  "key": "tab"}],
            "stop":         [{"action": "press",  "key": "s"}],
        },
    ),

    GameProfile(
        name="Generic FPS",
        exe_patterns=[],
        window_patterns=[],
        genre="fps",
        voice_commands={
            "jump":         "jump",
            "crouch":       "crouch",
            "reload":       "reload",
            "sprint":       "sprint",
            "stop":         "stop_moving",
            "walk forward": "walk_forward",
            "walk back":    "walk_back",
            "strafe left":  "strafe_left",
            "strafe right": "strafe_right",
        },
        macros={
            "jump":         [{"action": "press",  "key": "space"}],
            "crouch":       [{"action": "hold",   "key": "lctrl"}],
            "reload":       [{"action": "press",  "key": "r"}],
            "sprint":       [{"action": "hold",   "key": "lshift"}],
            "stop_moving":  [{"action": "release","key": "w"},
                             {"action": "release","key": "a"},
                             {"action": "release","key": "s"},
                             {"action": "release","key": "d"},
                             {"action": "release","key": "lshift"}],
            "walk_forward": [{"action": "hold",   "key": "w"}],
            "walk_back":    [{"action": "hold",   "key": "s"}],
            "strafe_left":  [{"action": "hold",   "key": "a"}],
            "strafe_right": [{"action": "hold",   "key": "d"}],
        },
    ),
]


class GameDetector:
    """
    Detects the currently active game and returns its profile.
    """

    def __init__(self, extra_profiles: Optional[List[GameProfile]] = None):
        self.profiles = list(BUILTIN_PROFILES)
        if extra_profiles:
            self.profiles.extend(extra_profiles)

    def get_running_processes(self) -> List[str]:
        """Return list of running process names (lowercase)."""
        try:
            import subprocess
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=5
            )
            names = []
            for line in result.stdout.splitlines():
                parts = line.strip('"').split('","')
                if parts:
                    names.append(parts[0].lower())
            return names
        except Exception as exc:
            logger.warning(f"Could not list processes: {exc}")
            return []

    def get_foreground_window_title(self) -> str:
        """Return the title of the currently focused window."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value.lower()
        except Exception:
            return ""

    def detect(self) -> Optional[GameProfile]:
        """
        Detect the active game.

        Checks foreground window title first (fast), then process list.
        Returns the matching GameProfile or None.
        """
        title = self.get_foreground_window_title()
        processes = self.get_running_processes()

        for profile in self.profiles:
            # Skip generic fallback during detection
            if not profile.exe_patterns and not profile.window_patterns:
                continue

            # Window title match
            for pattern in profile.window_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    logger.info(f"Detected game by window: {profile.name}")
                    return profile

            # Process match
            for proc in processes:
                for pattern in profile.exe_patterns:
                    if re.search(pattern, proc, re.IGNORECASE):
                        logger.info(f"Detected game by process: {profile.name}")
                        return profile

        logger.debug("No specific game detected")
        return None

    def get_profile(self, name: str) -> Optional[GameProfile]:
        """Get a profile by game name (case-insensitive)."""
        for p in self.profiles:
            if p.name.lower() == name.lower():
                return p
        return None

    def list_supported_games(self) -> List[str]:
        return [p.name for p in self.profiles]
