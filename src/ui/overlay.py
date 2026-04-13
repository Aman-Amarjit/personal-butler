"""
Desktop Overlay Rendering Engine

Handles PyQt6-based overlay rendering with slime body visualization
and interactive desktop integration.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from .slime_body import SlimeBody, AnimationState


def get_monitor_geometry(monitor_id: int = 0):
    """Return (x, y, w, h) for the requested monitor."""
    app = QApplication.instance()
    screens = app.screens() if app else []
    if not screens:
        return 0, 0, 1920, 1080
    idx = min(monitor_id, len(screens) - 1)
    geo = screens[idx].geometry()
    return geo.x(), geo.y(), geo.width(), geo.height()


class DesktopOverlay(QOpenGLWidget):
    """
    Transparent desktop overlay with slime body avatar.

    Controls:
      Escape  — quit
      Space   — toggle idle / listening state
      Click   — deform slime body
    """

    FPS = 60

    def __init__(self, monitor_id: int = 0):
        super().__init__()

        self.monitor_id = monitor_id
        self._mon_x, self._mon_y, self._mon_w, self._mon_h = get_monitor_geometry(monitor_id)

        # Slime body centred on the monitor
        self.slime = SlimeBody(
            position=(self._mon_w // 2, self._mon_h // 2),
            size=80,
            color="#00FFFF",
        )

        self._dt = 1.0 / self.FPS

        self._setup_window()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000 // self.FPS)

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("JARVIS")
        self.setGeometry(self._mon_x, self._mon_y, self._mon_w, self._mon_h)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        # Physics step
        self.slime.update_physics(self._dt)
        self.slime.animate_jiggle(self._dt)

        self._draw_slime(painter)
        self._draw_hud(painter)

    def _draw_slime(self, painter: QPainter) -> None:
        outline = self.slime.get_outline_points()
        if len(outline) < 3:
            return

        # Glow layers
        for glow in [20, 14, 8, 4]:
            painter.setPen(QPen(QColor(0, 255, 255, 25), glow))
            painter.drawPolyline([QPoint(int(x), int(y)) for x, y in outline])

        # Filled blob
        base_color, _ = self.slime.get_color_gradient()
        fill = QColor(base_color)
        fill.setAlpha(200)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(0, 255, 255, 255), 2))
        painter.drawPolygon([QPoint(int(x), int(y)) for x, y in outline])

        # Specular highlight
        painter.setBrush(QBrush(QColor(255, 255, 255, 90)))
        painter.setPen(Qt.PenStyle.NoPen)
        hx = int(self.slime.position.x - self.slime.current_size // 3)
        hy = int(self.slime.position.y - self.slime.current_size // 3)
        hs = int(self.slime.current_size // 2)
        painter.drawEllipse(hx, hy, hs, hs)

    def _draw_hud(self, painter: QPainter) -> None:
        painter.setPen(QColor(0, 255, 255, 180))
        painter.setFont(QFont("Consolas", 11))
        painter.drawText(16, 28, f"JARVIS  |  {self.slime.animation_state.value.upper()}")
        painter.drawText(16, 50, "ESC to quit  |  SPACE to toggle state")

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        pos = event.pos()
        self.slime.deform_on_interaction((pos.x(), pos.y()), intensity=0.8)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            self.slime.deform_on_interaction((pos.x(), pos.y()), intensity=0.3)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Space:
            next_state = (
                AnimationState.LISTENING
                if self.slime.animation_state == AnimationState.IDLE
                else AnimationState.IDLE
            )
            self.slime.set_animation_state(next_state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_animation_state(self, state: AnimationState) -> None:
        self.slime.set_animation_state(state)

    def set_slime_color(self, color: str) -> None:
        self.slime.set_color(color)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)


def create_overlay(monitor_id: int = 0) -> DesktopOverlay:
    return DesktopOverlay(monitor_id=monitor_id)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = create_overlay()
    overlay.show()
    sys.exit(app.exec())
