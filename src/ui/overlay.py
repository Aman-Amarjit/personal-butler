"""
PANDA AI Assistant — Professional Dark Glassmorphism UI

Frosted dark glass panel, draggable, bottom-right corner default.
Click-through is OFF (panel is interactive — drag to move, close button).
"""

import sys
import math
import random
from datetime import datetime
from typing import List, Optional, Tuple

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QRadialGradient, QLinearGradient, QPainterPath,
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from .slime_body import SlimeBody, AnimationState
from .visual_indicators import VisualIndicators, AlertLevel

# ── Layout ────────────────────────────────────────────────────────────────────
W      = 300
H      = 480
MARGIN = 18
RADIUS = 20
PAD    = 18
AV_CX  = W // 2
AV_CY  = 185
AV_R   = 68

# ── Colours ───────────────────────────────────────────────────────────────────
C_BG       = QColor(10,  12,  18,  230)
C_BORDER   = QColor(255, 255, 255,  18)
C_SURFACE  = QColor(255, 255, 255,   8)
C_TEXT_PRI = QColor(240, 242, 248, 230)
C_TEXT_SEC = QColor(160, 165, 185, 160)
C_TEXT_DIM = QColor(100, 105, 125, 120)
C_ACCENT   = QColor( 99, 179, 237, 255)
C_GREEN    = QColor( 72, 199, 142, 255)
C_ORANGE   = QColor(237, 137,  54, 255)
C_PURPLE   = QColor(183, 148, 246, 255)
C_RED      = QColor(252,  82,  82, 255)
C_GOLD     = QColor(246, 194,  62, 255)

STATE_ACCENT = {
    AnimationState.IDLE:       C_ACCENT,
    AnimationState.LISTENING:  C_GREEN,
    AnimationState.PROCESSING: C_ORANGE,
    AnimationState.SPEAKING:   C_PURPLE,
    AnimationState.ALERT:      C_RED,
    AnimationState.DANCING:    C_GOLD,
}

DANCE_PALETTE = [
    "#F6C23E", "#E74C3C", "#9B59B6", "#2ECC71",
    "#3498DB", "#E67E22", "#1ABC9C", "#E91E63",
]


def get_monitor_geometry(monitor_id: int = 0) -> Tuple[int, int, int, int]:
    app = QApplication.instance()
    screens = app.screens() if app else []
    if not screens:
        return 0, 0, 1920, 1080
    idx = min(monitor_id, len(screens) - 1)
    g = screens[idx].geometry()
    return g.x(), g.y(), g.width(), g.height()


# ── Particle ──────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "r", "color")

    def __init__(self, x: float, y: float, color: QColor):
        a = random.uniform(0, 2 * math.pi)
        s = random.uniform(15, 60)
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s - 20
        self.life = 1.0
        self.max_life = random.uniform(0.5, 1.4)
        self.r = random.uniform(2, 6)
        self.color = color

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 50 * dt
        self.life -= dt / self.max_life
        return self.life > 0


# ── Overlay ───────────────────────────────────────────────────────────────────
class DesktopOverlay(QOpenGLWidget):
    """
    Draggable PANDA panel.

    - Drag anywhere on the panel (except close button) to move it
    - Close button (×) top-right to quit
    - Stays on top of all windows
    """

    FPS = 60

    def __init__(self, monitor_id: int = 0):
        super().__init__()
        self.monitor_id = monitor_id
        mx, my, mw, mh = get_monitor_geometry(monitor_id)

        # Default position: bottom-right corner
        self._px = mx + mw - W - MARGIN
        self._py = my + mh - H - MARGIN

        self.slime = SlimeBody(
            position=(self._px + AV_CX, self._py + AV_CY),
            size=52, color="#63B3ED",
        )

        self._dt          = 1.0 / self.FPS
        self._t           = 0.0
        self._indicators  = VisualIndicators()
        self._particles: List[Particle] = []
        self._last_text   = ""
        self._bars        = [0.0] * 16
        self._pulse_r     = 0.0
        self._pulse_a     = 0.0
        self._spin_angle  = 0.0
        self._dance_idx   = 0
        self._dance_timer = 0.0

        # Drag state
        self._drag_active = False
        self._drag_offset = QPoint(0, 0)

        # Close button (local coords)
        self._close_rect = QRect(W - 30, 8, 22, 22)
        self._close_hov  = False

        # Stats
        self._cpu = 0.0
        self._mem = 0.0
        self._stats_t = QTimer(self)
        self._stats_t.timeout.connect(self._update_stats)
        self._stats_t.start(2000)
        self._update_stats()

        self._setup_window()

        self._render_t = QTimer(self)
        self._render_t.timeout.connect(self.update)
        self._render_t.start(1000 // self.FPS)

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("PANDA")
        self.setGeometry(self._px, self._py, W, H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _update_stats(self) -> None:
        try:
            import psutil
            self._cpu = psutil.cpu_percent(interval=None)
            self._mem = psutil.virtual_memory().percent
            if self._cpu > 80 or self._mem > 85:
                self._indicators.show_alert(
                    f"High load — CPU {self._cpu:.0f}%  RAM {self._mem:.0f}%",
                    AlertLevel.WARNING, duration=8.0,
                )
        except Exception:
            pass

    # ── Mouse events (drag + close) ───────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._close_rect.contains(event.pos()):
                self.close()
                QApplication.instance().quit()
                return
            # Start drag
            self._drag_active = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        self._close_hov = self._close_rect.contains(event.pos())
        if self._drag_active and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            # Keep slime position in sync with panel
            self._px = new_pos.x()
            self._py = new_pos.y()
            self.slime.position.x = self._px + AV_CX
            self.slime.position.y = self._py + AV_CY
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False

    def leaveEvent(self, event) -> None:
        self._close_hov = False
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        self._t += self._dt
        state = self.slime.animation_state
        acc   = STATE_ACCENT.get(state, C_ACCENT)

        # Update particles
        self._particles = [p for p in self._particles if p.update(self._dt)]

        # Waveform bars
        if state in (AnimationState.SPEAKING, AnimationState.DANCING):
            for i in range(len(self._bars)):
                self._bars[i] += (random.uniform(0.2, 1.0) - self._bars[i]) * 0.25
        else:
            for i in range(len(self._bars)):
                self._bars[i] *= 0.88

        # Pulse ring
        if state == AnimationState.LISTENING:
            self._pulse_r += self._dt * 55
            self._pulse_a = max(0.0, 1.0 - self._pulse_r / 110)
            if self._pulse_r > 110:
                self._pulse_r = 0.0
        else:
            self._pulse_a = 0.0

        # Processing spinner
        if state == AnimationState.PROCESSING:
            self._spin_angle = (self._spin_angle + 180 * self._dt) % 360

        # Dance colour cycle
        if state == AnimationState.DANCING:
            self._dance_timer += self._dt
            if self._dance_timer >= 0.22:
                self._dance_timer = 0.0
                self._dance_idx = (self._dance_idx + 1) % len(DANCE_PALETTE)
                self.slime.set_color(DANCE_PALETTE[self._dance_idx])
            if random.random() < 0.25:
                self._spawn_particles(2)

        self.slime.update_physics(self._dt)
        self.slime.animate_jiggle(self._dt)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))

        self._draw_glass(p, acc)
        self._draw_close(p)
        self._draw_header(p, acc)
        self._draw_avatar_area(p, acc, state)
        self._draw_status_badge(p, acc, state)
        self._draw_last_text(p)
        self._draw_stats(p, acc)
        self._draw_bars(p, acc)
        self._draw_alert(p)

    # ── Glass panel ───────────────────────────────────────────────────────────

    def _draw_glass(self, p: QPainter, acc: QColor) -> None:
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, W, H), RADIUS, RADIUS)

        # Background
        p.setBrush(QBrush(C_BG))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        # Top sheen
        sheen = QLinearGradient(0, 0, 0, H * 0.35)
        sheen.setColorAt(0, QColor(255, 255, 255, 14))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(sheen))
        p.drawPath(path)

        # Accent glow border
        glow = QColor(acc)
        glow.setAlpha(55)
        p.setPen(QPen(glow, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # White hairline
        p.setPen(QPen(C_BORDER, 0.8))
        p.drawPath(path)

        # Drag hint — subtle grip dots at top-centre
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            dot = QColor(255, 255, 255, 35)
            p.setBrush(QBrush(dot))
            p.drawEllipse(W // 2 - 12 + i * 12, 10, 4, 4)

    # ── Close button ──────────────────────────────────────────────────────────

    def _draw_close(self, p: QPainter) -> None:
        r = self._close_rect
        bg = QColor(220, 50, 50, 220) if self._close_hov else QColor(60, 20, 20, 180)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(200, 80, 80, 160), 1))
        p.drawEllipse(r)
        p.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        pad = 7
        p.drawLine(r.left() + pad, r.top() + pad, r.right() - pad, r.bottom() - pad)
        p.drawLine(r.right() - pad, r.top() + pad, r.left() + pad, r.bottom() - pad)

    # ── Header ────────────────────────────────────────────────────────────────

    def _draw_header(self, p: QPainter, acc: QColor) -> None:
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.setPen(QColor(acc))
        p.drawText(QRect(PAD, 14, W // 2, 22), Qt.AlignmentFlag.AlignLeft, "PANDA")

        p.setFont(QFont("Segoe UI", 11))
        p.setPen(C_TEXT_SEC)
        p.drawText(QRect(0, 14, W - PAD, 22), Qt.AlignmentFlag.AlignRight,
                   datetime.now().strftime("%H:%M"))

        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawLine(PAD, 40, W - PAD, 40)

    # ── Avatar area ───────────────────────────────────────────────────────────

    def _draw_avatar_area(self, p: QPainter, acc: QColor, state: AnimationState) -> None:
        cx, cy = AV_CX, AV_CY

        # Pulse ring
        if self._pulse_a > 0:
            r = int(self._pulse_r) + AV_R
            col = QColor(C_GREEN)
            col.setAlpha(int(self._pulse_a * 120))
            p.setPen(QPen(col, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Processing arc
        if state == AnimationState.PROCESSING:
            p.setPen(QPen(C_ORANGE, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(cx - AV_R - 8, cy - AV_R - 8, (AV_R + 8) * 2, (AV_R + 8) * 2,
                      int(self._spin_angle * 16), int(240 * 16))

        # Avatar halo
        grad = QRadialGradient(cx - AV_R // 3, cy - AV_R // 3, AV_R * 1.2)
        base = QColor(acc)
        base.setAlpha(30)
        grad.setColorAt(0, base)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - AV_R, cy - AV_R, AV_R * 2, AV_R * 2)

        # Slime body
        outline = self.slime.get_outline_points()
        if len(outline) >= 3:
            pts = [QPoint(int(x) - self._px, int(y) - self._py) for x, y in outline]
            sc = QColor(self.slime.color)

            for w, a in [(18, 12), (10, 25), (5, 50)]:
                gc = QColor(sc); gc.setAlpha(a)
                p.setPen(QPen(gc, w))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPolyline(pts)

            fc = QColor(sc); fc.setAlpha(200)
            p.setBrush(QBrush(fc))
            p.setPen(QPen(sc, 1.5))
            p.drawPolygon(pts)

            sg = QRadialGradient(cx - AV_R // 3, cy - AV_R // 3, AV_R // 2)
            sg.setColorAt(0, QColor(255, 255, 255, 90))
            sg.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(sg))
            p.setPen(Qt.PenStyle.NoPen)
            sz = int(self.slime.current_size)
            p.drawEllipse(cx - sz, cy - sz, sz * 2, sz * 2)

            # Eyes
            eye_r = max(3, sz // 7)
            blink = abs(math.sin(self._t * 0.35)) > 0.96
            if not blink:
                eo = sz // 3
                for ex, ey in [(cx - eo, cy - eo // 2), (cx + eo, cy - eo // 2)]:
                    p.setBrush(QBrush(QColor(255, 255, 255, 230)))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(ex - eye_r, ey - eye_r, eye_r * 2, eye_r * 2)
                    pr = max(1, eye_r // 2)
                    p.setBrush(QBrush(QColor(15, 15, 30, 230)))
                    p.drawEllipse(ex - pr, ey - pr, pr * 2, pr * 2)

        # Particles
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self._particles:
            c = QColor(pt.color)
            c.setAlphaF(pt.life * 0.85)
            p.setBrush(QBrush(c))
            s = max(1, int(pt.r * pt.life))
            px = int(pt.x) - self._px
            py = int(pt.y) - self._py
            p.drawEllipse(px - s // 2, py - s // 2, s, s)

    # ── Status badge ──────────────────────────────────────────────────────────

    def _draw_status_badge(self, p: QPainter, acc: QColor, state: AnimationState) -> None:
        label = state.value.upper()
        y = AV_CY + AV_R + 18

        dot_col = QColor(acc)
        if state == AnimationState.IDLE:
            dot_col.setAlpha(int(160 + 80 * math.sin(self._t * 2)))
        p.setBrush(QBrush(dot_col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(W // 2 - 38, y + 4, 8, 8)

        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        p.setPen(QColor(acc))
        p.drawText(QRect(W // 2 - 26, y, 80, 18), Qt.AlignmentFlag.AlignLeft, label)

    # ── Last heard text ───────────────────────────────────────────────────────

    def _draw_last_text(self, p: QPainter) -> None:
        if not self._last_text:
            return
        y = AV_CY + AV_R + 42
        txt = self._last_text if len(self._last_text) <= 38 else self._last_text[:35] + "…"

        card = QPainterPath()
        card.addRoundedRect(QRectF(PAD, y, W - PAD * 2, 28), 8, 8)
        p.setBrush(QBrush(C_SURFACE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(card)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(C_TEXT_SEC)
        p.drawText(QRect(PAD + 10, y, W - PAD * 2 - 10, 28),
                   Qt.AlignmentFlag.AlignVCenter, f'"{txt}"')

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _draw_stats(self, p: QPainter, acc: QColor) -> None:
        y0 = AV_CY + AV_R + 80

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(C_TEXT_DIM)
        p.drawText(QRect(PAD, y0, W - PAD * 2, 16),
                   Qt.AlignmentFlag.AlignLeft,
                   datetime.now().strftime("%A, %d %B"))

        self._draw_bar_row(p, y0 + 22, "CPU", self._cpu, C_ACCENT)
        self._draw_bar_row(p, y0 + 42, "RAM", self._mem, C_PURPLE)

    def _draw_bar_row(self, p: QPainter, y: int, label: str,
                      pct: float, col: QColor) -> None:
        bx = PAD + 36
        bw = W - PAD * 2 - 36
        bh = 5

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(C_TEXT_DIM)
        p.drawText(QRect(PAD, y, 34, bh + 4), Qt.AlignmentFlag.AlignVCenter, label)

        track = QPainterPath()
        track.addRoundedRect(QRectF(bx, y, bw, bh), 3, 3)
        p.setBrush(QBrush(QColor(255, 255, 255, 15)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(track)

        fw = int(bw * min(pct, 100) / 100)
        if fw > 2:
            fill_col = C_RED if pct > 80 else col
            grad = QLinearGradient(bx, 0, bx + fw, 0)
            fc = QColor(fill_col); fc.setAlpha(200)
            grad.setColorAt(0, fc)
            fc2 = QColor(fill_col); fc2.setAlpha(255)
            grad.setColorAt(1, fc2)
            fill = QPainterPath()
            fill.addRoundedRect(QRectF(bx, y, fw, bh), 3, 3)
            p.setBrush(QBrush(grad))
            p.drawPath(fill)

        p.setFont(QFont("Segoe UI", 7))
        p.setPen(C_TEXT_DIM)
        p.drawText(QRect(bx + bw + 4, y, 28, bh + 4),
                   Qt.AlignmentFlag.AlignVCenter, f"{pct:.0f}%")

    # ── Waveform bars ─────────────────────────────────────────────────────────

    def _draw_bars(self, p: QPainter, acc: QColor) -> None:
        if max(self._bars) < 0.04:
            return
        y0 = H - 52
        bw = 8; gap = 4
        total = len(self._bars) * (bw + gap) - gap
        x0 = W // 2 - total // 2

        for i, h in enumerate(self._bars):
            bh = max(2, int(h * 28))
            bx = x0 + i * (bw + gap)
            by = y0 + (28 - bh) // 2
            col = QColor(acc)
            col.setAlpha(int(60 + 180 * h))
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            path.addRoundedRect(QRectF(bx, by, bw, bh), 3, 3)
            p.drawPath(path)

    # ── Alert banner ──────────────────────────────────────────────────────────

    def _draw_alert(self, p: QPainter) -> None:
        states = self._indicators.update(self._dt)
        alert  = states["alert"]
        if not alert["visible"]:
            return
        r, g, b, _ = alert["color"]
        path = QPainterPath()
        path.addRoundedRect(QRectF(PAD, H - 30, W - PAD * 2, 22), 6, 6)
        p.setBrush(QBrush(QColor(r, g, b, 200)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        p.setPen(QColor(255, 255, 255, 230))
        p.drawText(QRect(PAD, H - 30, W - PAD * 2, 22),
                   Qt.AlignmentFlag.AlignCenter, alert["message"])

    # ── Particles ─────────────────────────────────────────────────────────────

    def _spawn_particles(self, n: int = 12) -> None:
        state = self.slime.animation_state
        if state == AnimationState.DANCING:
            col = QColor(DANCE_PALETTE[self._dance_idx])
        else:
            col = QColor(STATE_ACCENT.get(state, C_ACCENT))
        cx = int(self.slime.position.x)
        cy = int(self.slime.position.y)
        for _ in range(n):
            self._particles.append(Particle(cx, cy, col))

    # ── Public API ────────────────────────────────────────────────────────────

    def set_animation_state(self, state: AnimationState) -> None:
        prev = self.slime.animation_state
        self.slime.set_animation_state(state)
        self._indicators.set_processing(state == AnimationState.PROCESSING)
        if state != prev:
            self._spawn_particles(18 if state == AnimationState.DANCING else 12)
        if state != AnimationState.DANCING:
            col = STATE_ACCENT.get(state, C_ACCENT)
            self.slime.set_color(f"#{col.red():02X}{col.green():02X}{col.blue():02X}")

    def set_last_text(self, text: str) -> None:
        self._last_text = text

    def set_slime_color(self, color: str) -> None:
        self.slime.set_color(color)

    def show_alert(self, msg: str, level: AlertLevel = AlertLevel.INFO,
                   duration: float = 5.0) -> None:
        self._indicators.show_alert(msg, level, duration)

    def set_camera_active(self, active: bool) -> None:
        self._indicators.set_camera_active(active)

    def set_privacy_mode(self, enabled: bool) -> None:
        self._indicators.set_privacy_mode(enabled)

    def closeEvent(self, event) -> None:
        self._render_t.stop()
        self._stats_t.stop()
        super().closeEvent(event)


def create_overlay(monitor_id: int = 0) -> DesktopOverlay:
    return DesktopOverlay(monitor_id=monitor_id)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = create_overlay()
    overlay.show()
    sys.exit(app.exec())
