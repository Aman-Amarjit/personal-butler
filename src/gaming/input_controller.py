"""
Input Controller - Keyboard and mouse automation for game control.

Uses ctypes (Windows) for low-level input injection that works in
most games, with a pynput fallback for non-game applications.
"""

import ctypes
import ctypes.wintypes
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger("panda.gaming.input")

# ── Windows virtual key codes ──────────────────────────────────────────────
VK = {
    # Movement
    "w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    # Actions
    "space": 0x20, "enter": 0x0D, "escape": 0x1B, "tab": 0x09,
    "shift": 0x10, "ctrl": 0x11, "alt": 0x12,
    "lshift": 0xA0, "rshift": 0xA1,
    "lctrl": 0xA2, "rctrl": 0xA3,
    # Numbers
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
    "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30,
    # Function keys
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    # Common game keys
    "r": 0x52, "e": 0x45, "q": 0x51, "f": 0x46,
    "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E,
    "o": 0x4F, "p": 0x50, "t": 0x54, "u": 0x55,
    "v": 0x56, "x": 0x58, "y": 0x59, "z": 0x5A,
    "b": 0x42, "c": 0x43,
    # Mouse buttons (used as identifiers, not VK codes)
    "lmb": "lmb", "rmb": "rmb", "mmb": "mmb",
}

# Windows INPUT structures
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class _InputUnion(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _InputUnion)]

KEYEVENTF_KEYUP   = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD    = 1
INPUT_MOUSE       = 0
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040
MOUSEEVENTF_ABSOLUTE    = 0x8000


def _send_input(*inputs: Input) -> None:
    n = len(inputs)
    arr = (Input * n)(*inputs)
    ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(Input))


def _key_input(vk: int, key_up: bool = False) -> Input:
    flags = KEYEVENTF_KEYUP if key_up else 0
    extra = ctypes.c_ulong(0)
    ki = KeyBdInput(wVk=vk, wScan=0, dwFlags=flags, time=0,
                    dwExtraInfo=ctypes.pointer(extra))
    ii = _InputUnion(ki=ki)
    return Input(type=INPUT_KEYBOARD, ii=ii)


def _mouse_input(flags: int, dx: int = 0, dy: int = 0) -> Input:
    extra = ctypes.c_ulong(0)
    mi = MouseInput(dx=dx, dy=dy, mouseData=0, dwFlags=flags, time=0,
                    dwExtraInfo=ctypes.pointer(extra))
    ii = _InputUnion(mi=mi)
    return Input(type=INPUT_MOUSE, ii=ii)


@dataclass
class MacroStep:
    """One step in a macro sequence."""
    action: str          # "press", "hold", "release", "move", "click", "wait"
    key: str = ""
    duration: float = 0.0
    x: int = 0
    y: int = 0


class InputController:
    """
    Low-level keyboard and mouse controller for game automation.

    Supports:
    - Key press / hold / release
    - Mouse move and click
    - Macro sequences (combo moves)
    - Held-key management (e.g. hold W to walk)
    """

    def __init__(self):
        self._held: set = set()
        self._lock = threading.Lock()
        self._macro_thread: Optional[threading.Thread] = None
        self._stop_macro = threading.Event()

    # ── Keyboard ──────────────────────────────────────────────────────────

    def press(self, key: str) -> bool:
        """Tap a key (down + up)."""
        vk = self._resolve_vk(key)
        if vk is None:
            return False
        _send_input(_key_input(vk, False), _key_input(vk, True))
        logger.debug(f"press {key}")
        return True

    def hold(self, key: str) -> bool:
        """Hold a key down until release() is called."""
        vk = self._resolve_vk(key)
        if vk is None:
            return False
        with self._lock:
            if key in self._held:
                return True
            self._held.add(key)
        _send_input(_key_input(vk, False))
        logger.debug(f"hold {key}")
        return True

    def release(self, key: str) -> bool:
        """Release a held key."""
        vk = self._resolve_vk(key)
        if vk is None:
            return False
        with self._lock:
            self._held.discard(key)
        _send_input(_key_input(vk, True))
        logger.debug(f"release {key}")
        return True

    def release_all(self) -> None:
        """Release every currently held key."""
        with self._lock:
            held = list(self._held)
        for key in held:
            self.release(key)

    def hold_for(self, key: str, seconds: float) -> None:
        """Hold a key for a fixed duration (blocking)."""
        self.hold(key)
        time.sleep(seconds)
        self.release(key)

    def combo(self, *keys: str, hold_ms: int = 50) -> None:
        """Press a key combination (e.g. ctrl+c)."""
        vks = [self._resolve_vk(k) for k in keys]
        if None in vks:
            logger.warning(f"Unknown key in combo: {keys}")
            return
        for vk in vks:
            _send_input(_key_input(vk, False))
        time.sleep(hold_ms / 1000)
        for vk in reversed(vks):
            _send_input(_key_input(vk, True))

    # ── Mouse ─────────────────────────────────────────────────────────────

    def move_mouse(self, x: int, y: int, absolute: bool = True) -> None:
        """Move mouse to (x, y). Absolute coords by default."""
        if absolute:
            # Normalise to 0-65535 range required by MOUSEEVENTF_ABSOLUTE
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            nx = int(x * 65535 / sw)
            ny = int(y * 65535 / sh)
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
            _send_input(_mouse_input(flags, nx, ny))
        else:
            _send_input(_mouse_input(MOUSEEVENTF_MOVE, x, y))

    def click(self, button: str = "lmb", x: Optional[int] = None,
              y: Optional[int] = None) -> None:
        """Click a mouse button, optionally moving first."""
        if x is not None and y is not None:
            self.move_mouse(x, y)
            time.sleep(0.05)
        down_flag, up_flag = {
            "lmb": (MOUSEEVENTF_LEFTDOWN,   MOUSEEVENTF_LEFTUP),
            "rmb": (MOUSEEVENTF_RIGHTDOWN,  MOUSEEVENTF_RIGHTUP),
            "mmb": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
        }.get(button, (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP))
        _send_input(_mouse_input(down_flag), _mouse_input(up_flag))

    # ── Macros ────────────────────────────────────────────────────────────

    def run_macro(self, steps: List[MacroStep], blocking: bool = False) -> None:
        """Execute a macro sequence."""
        self._stop_macro.clear()

        def _run():
            for step in steps:
                if self._stop_macro.is_set():
                    break
                if step.action == "press":
                    self.press(step.key)
                elif step.action == "hold":
                    self.hold(step.key)
                elif step.action == "release":
                    self.release(step.key)
                elif step.action == "move":
                    self.move_mouse(step.x, step.y)
                elif step.action == "click":
                    self.click(step.key or "lmb", step.x or None, step.y or None)
                elif step.action == "wait":
                    time.sleep(step.duration)
                if step.duration > 0 and step.action not in ("wait",):
                    time.sleep(step.duration)
            self.release_all()

        if blocking:
            _run()
        else:
            self._macro_thread = threading.Thread(target=_run, daemon=True)
            self._macro_thread.start()

    def stop_macro(self) -> None:
        """Abort a running macro."""
        self._stop_macro.set()
        self.release_all()

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_vk(key: str) -> Optional[int]:
        key = key.lower()
        vk = VK.get(key)
        if vk is None or isinstance(vk, str):
            return None
        return vk
