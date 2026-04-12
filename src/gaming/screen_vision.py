"""
Screen Vision - Answers questions about what's on screen using Ollama.

Captures the screen, encodes it, and sends it to an Ollama vision model
(llava or moondream) so JARVIS can describe or reason about what it sees.
Falls back to a text description of pixel statistics when no vision model
is available.
"""

import base64
import io
import logging
import time
from typing import Optional

import requests

from .screen_reader import ScreenReader, ScreenRegion, ScreenCapture

logger = logging.getLogger("jarvis.gaming.vision")

# Vision models to try in order of preference
VISION_MODELS = ["llava:7b", "llava:13b", "moondream", "llava"]


class ScreenVision:
    """
    Answers natural-language questions about the current screen.

    Uses Ollama vision models (llava / moondream).  Falls back to a
    pixel-statistics description when no vision model is available.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.reader = ScreenReader()
        self._vision_model: Optional[str] = None
        self._model_checked = False

    # ── Model discovery ───────────────────────────────────────────────────

    def _find_vision_model(self) -> Optional[str]:
        """Return the first available vision model, or None."""
        if self._model_checked:
            return self._vision_model
        self._model_checked = True
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return None
            available = {m["name"] for m in resp.json().get("models", [])}
            for candidate in VISION_MODELS:
                if any(candidate in a for a in available):
                    self._vision_model = candidate
                    logger.info(f"Vision model: {candidate}")
                    return candidate
        except Exception as exc:
            logger.warning(f"Could not query Ollama models: {exc}")
        return None

    # ── Core API ──────────────────────────────────────────────────────────

    def ask(self, question: str, region: Optional[ScreenRegion] = None) -> str:
        """
        Capture the screen and answer a question about it.

        Args:
            question: Natural-language question (e.g. "what game is this?")
            region:   Optional sub-region to capture (full screen if None)

        Returns:
            Answer string
        """
        capture = self.reader.capture(region)
        if capture is None:
            return "I couldn't capture the screen right now."

        model = self._find_vision_model()
        if model:
            return self._ask_vision_model(model, capture, question)
        return self._describe_fallback(capture, question)

    def describe_screen(self, region: Optional[ScreenRegion] = None) -> str:
        """Describe what's currently on screen."""
        return self.ask("Describe what you see on the screen in detail.", region)

    def what_game(self) -> str:
        """Try to identify the game currently on screen."""
        return self.ask(
            "What game is being played on this screen? "
            "Give the game name and a brief description of what's happening."
        )

    def read_text(self, region: Optional[ScreenRegion] = None) -> str:
        """Read visible text from the screen."""
        return self.ask(
            "Read all visible text on the screen and list it clearly.",
            region,
        )

    def game_state(self) -> str:
        """Describe the current game state (health, score, position, etc.)."""
        return self.ask(
            "Describe the current game state: health, score, ammo, position, "
            "enemies visible, objectives, and any important UI elements."
        )

    def suggest_action(self, context: str = "") -> str:
        """Ask the AI what action to take next in the game."""
        prompt = (
            "You are an expert game AI assistant. "
            "Look at this game screenshot and suggest the single best action "
            "to take right now. Be specific and concise (one sentence). "
        )
        if context:
            prompt += f"Context: {context}"
        return self.ask(prompt)

    # ── Vision model call ─────────────────────────────────────────────────

    def _ask_vision_model(
        self, model: str, capture: ScreenCapture, question: str
    ) -> str:
        """Send capture + question to Ollama vision model."""
        try:
            img_b64 = self._capture_to_base64(capture)
            payload = {
                "model": model,
                "prompt": question,
                "images": [img_b64],
                "stream": False,
                "options": {"num_predict": 300},
            }
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            logger.warning(f"Vision model returned {resp.status_code}")
            return self._describe_fallback(capture, question)
        except Exception as exc:
            logger.error(f"Vision model error: {exc}")
            return self._describe_fallback(capture, question)

    # ── Fallback description ──────────────────────────────────────────────

    def _describe_fallback(self, capture: ScreenCapture, question: str) -> str:
        """
        Produce a basic description from pixel statistics when no vision
        model is available.
        """
        try:
            # Sample a grid of pixels for dominant colors
            step = max(1, min(capture.width, capture.height) // 20)
            color_counts: dict = {}
            for py in range(0, capture.height, step):
                for px in range(0, capture.width, step):
                    b, g, r, _ = self.reader.get_pixel(capture, px, py)
                    bucket = (r // 64 * 64, g // 64 * 64, b // 64 * 64)
                    color_counts[bucket] = color_counts.get(bucket, 0) + 1

            top = sorted(color_counts, key=color_counts.get, reverse=True)[:3]
            color_desc = ", ".join(f"RGB({r},{g},{b})" for r, g, b in top)

            brightness = sum(
                (self.reader.get_pixel(capture, px, py)[2] +
                 self.reader.get_pixel(capture, px, py)[1] +
                 self.reader.get_pixel(capture, px, py)[0]) // 3
                for py in range(0, capture.height, step * 4)
                for px in range(0, capture.width, step * 4)
            ) // max(1, (capture.height // (step * 4)) * (capture.width // (step * 4)))

            mood = "bright" if brightness > 160 else "dark" if brightness < 80 else "medium-lit"
            return (
                f"Screen is {capture.width}×{capture.height}, {mood}. "
                f"Dominant colors: {color_desc}. "
                f"(Install a vision model with 'ollama pull llava' for detailed answers.)"
            )
        except Exception:
            return "Screen captured but could not be analysed. Install llava with 'ollama pull llava'."

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _capture_to_base64(capture: ScreenCapture) -> str:
        """Convert raw BGRA bytes to a PNG base64 string."""
        try:
            from PIL import Image
            img = Image.frombytes(
                "RGBA", (capture.width, capture.height),
                capture.data, "raw", "BGRA"
            )
            # Downscale to max 1280px wide to keep payload small
            if img.width > 1280:
                ratio = 1280 / img.width
                img = img.resize(
                    (1280, int(img.height * ratio)), Image.LANCZOS
                )
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=75)
            return base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            # No Pillow — encode raw BGRA as BMP manually
            return base64.b64encode(capture.data[:1024 * 1024]).decode()
