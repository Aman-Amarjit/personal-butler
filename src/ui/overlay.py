"""
Desktop Overlay Rendering Engine

Handles PyQt6-based overlay rendering with slime body visualization
and interactive desktop integration.
"""

import sys
from typing import Optional, Tuple
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from .slime_body import SlimeBody, AnimationState, Vector2


def get_monitor_geometry(monitor_id: int = 0):
    """
    Return (x, y, width, height) for the requested monitor.

    Falls back to primary monitor geometry if monitor_id is out of range.
    """
    app = QApplication.instance()
    screens = app.screens() if app else []
    if not screens:
        return 0, 0, 1920, 1080
    idx = min(monitor_id, len(screens) - 1)
    geo = screens[idx].geometry()
    return geo.x(), geo.y(), geo.width(), geo.height()


class DesktopOverlay(QOpenGLWidget):
    """
    Desktop overlay widget with slime body rendering.

    Features:
    - Transparent overlay on desktop
    - Slime body physics simulation
    - Interactive animations
    - Multi-monitor support
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        monitor_id: int = 0
    ):
        """
        Initialize the desktop overlay.

        Args:
            width: Overlay width in pixels
            height: Overlay height in pixels
            monitor_id: Target monitor index
        """
        super().__init__()

        self.width = width
        self.height = height
        self.monitor_id = monitor_id

        # Slime body
        self.slime = SlimeBody(
            position=(width // 2, height // 2),
            size=80,
            color="#00FFFF"
        )

        # Rendering
        self.fps = 60
        self.frame_time = 1000 // self.fps  # milliseconds
        self.delta_time = self.frame_time / 1000.0

        # Multi-monitor: position on the correct screen
        self._monitor_x, self._monitor_y, self.width, self.height = get_monitor_geometry(monitor_id)

        # Setup window
        self._setup_window()

        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.frame_time)

    def _setup_window(self) -> None:
        """Configure window properties for overlay"""
        self.setWindowTitle("JARVIS Overlay")
        self.setGeometry(self._monitor_x, self._monitor_y, self.width, self.height)

        # Make window transparent and always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.TranslucentBackground
        )

        # Set transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:
        """
        Render the overlay.

        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear background (transparent)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        # Update slime physics
        self.slime.update_physics(self.delta_time)
        self.slime.animate_jiggle(self.delta_time)

        # Draw slime body
        self._draw_slime_body(painter)

        # Draw UI elements
        self._draw_ui_elements(painter)

    def _draw_slime_body(self, painter: QPainter) -> None:
        """
        Draw the slime body with glow effect.

        Args:
            painter: QPainter instance
        """
        outline = self.slime.get_outline_points()

        if len(outline) < 3:
            return

        # Draw glow effect (multiple layers)
        for glow_size in [20, 15, 10, 5]:
            glow_color = QColor(0, 255, 255, 30)
            painter.setPen(QPen(glow_color, glow_size))
            painter.drawPolyline(
                [QPoint(int(x), int(y)) for x, y in outline]
            )

        # Draw main blob
        base_color, _ = self.slime.get_color_gradient()
        blob_color = QColor(base_color)
        blob_color.setAlpha(200)

        painter.setBrush(QBrush(blob_color))
        painter.setPen(QPen(QColor(0, 255, 255, 255), 2))

        points = [QPoint(int(x), int(y)) for x, y in outline]
        painter.drawPolygon(points)

        # Draw highlight
        highlight_color = QColor(255, 255, 255, 100)
        painter.setBrush(QBrush(highlight_color))
        painter.setPen(Qt.PenStyle.NoPen)

        # Highlight on top-left
        highlight_x = self.slime.position.x - self.slime.current_size // 3
        highlight_y = self.slime.position.y - self.slime.current_size // 3
        painter.drawEllipse(
            int(highlight_x),
            int(highlight_y),
            int(self.slime.current_size // 2),
            int(self.slime.current_size // 2)
        )

    def _draw_ui_elements(self, painter: QPainter) -> None:
        """
        Draw UI elements (status, info, etc).

        Args:
            painter: QPainter instance
        """
        # Draw status text
        painter.setPen(QColor(0, 255, 255, 200))
        font = QFont("Arial", 12)
        painter.setFont(font)

        status_text = f"State: {self.slime.animation_state.value}"
        painter.drawText(20, 30, status_text)

        # Draw FPS
        fps_text = f"FPS: {self.fps}"
        painter.drawText(20, 60, fps_text)

    def mousePressEvent(self, event) -> None:
        """
        Handle mouse press events.

        Args:
            event: Mouse event
        """
        pos = event.pos()
        self.slime.deform_on_interaction(
            (pos.x(), pos.y()),
            intensity=0.8
        )

    def mouseMoveEvent(self, event) -> None:
        """
        Handle mouse move events.

        Args:
            event: Mouse event
        """
        if event.buttons() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            self.slime.deform_on_interaction(
                (pos.x(), pos.y()),
                intensity=0.3
            )

    def keyPressEvent(self, event) -> None:
        """
        Handle keyboard events.

        Args:
            event: Key event
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Space:
            # Toggle animation state
            if self.slime.animation_state == AnimationState.IDLE:
                self.slime.set_animation_state(AnimationState.LISTENING)
            else:
                self.slime.set_animation_state(AnimationState.IDLE)

    def set_animation_state(self, state: AnimationState) -> None:
        """
        Set the slime body animation state.

        Args:
            state: New animation state
        """
        self.slime.set_animation_state(state)

    def set_slime_color(self, color: str) -> None:
        """
        Set the slime body color.

        Args:
            color: Hex color code
        """
        self.slime.set_color(color)

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Args:
            event: Close event
        """
        self.timer.stop()
        super().closeEvent(event)


def create_overlay(
    width: int = 1920,
    height: int = 1080,
    monitor_id: int = 0
) -> DesktopOverlay:
    """
    Create and return a desktop overlay instance.

    Args:
        width: Overlay width
        height: Overlay height
        monitor_id: Target monitor

    Returns:
        DesktopOverlay instance
    """
    return DesktopOverlay(width, height, monitor_id)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = create_overlay()
    overlay.show()
    sys.exit(app.exec())
