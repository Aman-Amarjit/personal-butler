"""
Screen Reader - Captures and analyses the game screen.

Uses the Windows GDI BitBlt for fast capture (no extra deps),
with optional PIL/Pillow for image processing.
"""

import ctypes
import ctypes.wintypes
import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("panda.gaming.screen")


@dataclass
class ScreenRegion:
    x: int
    y: int
    width: int
    height: int


@dataclass
class ScreenCapture:
    data: bytes          # raw BGRA bytes
    width: int
    height: int
    timestamp: float


class ScreenReader:
    """
    Captures screen regions using Windows GDI (no extra install needed).

    Optionally converts to PIL Image for pixel analysis.
    """

    def __init__(self):
        self._user32  = ctypes.windll.user32
        self._gdi32   = ctypes.windll.gdi32
        self._kernel32 = ctypes.windll.kernel32

    # ── Capture ───────────────────────────────────────────────────────────

    def capture(self, region: Optional[ScreenRegion] = None) -> Optional[ScreenCapture]:
        """
        Capture a screen region (or full screen if region is None).

        Returns ScreenCapture with raw BGRA bytes, or None on failure.
        """
        try:
            if region is None:
                x, y = 0, 0
                w = self._user32.GetSystemMetrics(0)
                h = self._user32.GetSystemMetrics(1)
            else:
                x, y, w, h = region.x, region.y, region.width, region.height

            hdc_screen = self._user32.GetDC(None)
            hdc_mem    = self._gdi32.CreateCompatibleDC(hdc_screen)
            hbm        = self._gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            self._gdi32.SelectObject(hdc_mem, hbm)
            self._gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020)  # SRCCOPY

            # Extract pixel data
            buf_size = w * h * 4
            buf = (ctypes.c_char * buf_size)()

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize",          ctypes.c_uint32),
                    ("biWidth",         ctypes.c_int32),
                    ("biHeight",        ctypes.c_int32),
                    ("biPlanes",        ctypes.c_uint16),
                    ("biBitCount",      ctypes.c_uint16),
                    ("biCompression",   ctypes.c_uint32),
                    ("biSizeImage",     ctypes.c_uint32),
                    ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed",       ctypes.c_uint32),
                    ("biClrImportant",  ctypes.c_uint32),
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize        = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth       = w
            bmi.biHeight      = -h   # top-down
            bmi.biPlanes      = 1
            bmi.biBitCount    = 32
            bmi.biCompression = 0    # BI_RGB

            self._gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bmi), 0)

            # Cleanup
            self._gdi32.DeleteObject(hbm)
            self._gdi32.DeleteDC(hdc_mem)
            self._user32.ReleaseDC(None, hdc_screen)

            return ScreenCapture(
                data=bytes(buf),
                width=w,
                height=h,
                timestamp=time.monotonic(),
            )
        except Exception as exc:
            logger.error(f"Screen capture failed: {exc}")
            return None

    def to_pil(self, capture: ScreenCapture):
        """Convert a ScreenCapture to a PIL Image (requires Pillow)."""
        try:
            from PIL import Image
            img = Image.frombytes("RGBA", (capture.width, capture.height), capture.data, "raw", "BGRA")
            return img
        except ImportError:
            logger.warning("Pillow not installed — cannot convert to PIL Image")
            return None

    # ── Pixel analysis ────────────────────────────────────────────────────

    def get_pixel(self, capture: ScreenCapture, x: int, y: int) -> Tuple[int, int, int, int]:
        """Return (B, G, R, A) at pixel (x, y)."""
        offset = (y * capture.width + x) * 4
        b, g, r, a = capture.data[offset:offset + 4]
        return int(b), int(g), int(r), int(a)

    def find_color(
        self,
        capture: ScreenCapture,
        r: int, g: int, b: int,
        tolerance: int = 10,
    ) -> Optional[Tuple[int, int]]:
        """
        Find the first pixel matching (r, g, b) within tolerance.

        Returns (x, y) or None.
        """
        for py in range(capture.height):
            for px in range(capture.width):
                pb, pg, pr, _ = self.get_pixel(capture, px, py)
                if (abs(pr - r) <= tolerance and
                        abs(pg - g) <= tolerance and
                        abs(pb - b) <= tolerance):
                    return px, py
        return None

    def average_color(
        self,
        capture: ScreenCapture,
        region: Optional[ScreenRegion] = None,
    ) -> Tuple[int, int, int]:
        """Return average (R, G, B) of a region (or full capture)."""
        x0 = region.x if region else 0
        y0 = region.y if region else 0
        x1 = (region.x + region.width)  if region else capture.width
        y1 = (region.y + region.height) if region else capture.height

        total_r = total_g = total_b = count = 0
        for py in range(y0, y1):
            for px in range(x0, x1):
                pb, pg, pr, _ = self.get_pixel(capture, px, py)
                total_r += pr; total_g += pg; total_b += pb
                count += 1

        if count == 0:
            return 0, 0, 0
        return total_r // count, total_g // count, total_b // count
