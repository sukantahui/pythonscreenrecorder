"""
Cinematic animated countdown overlay (3... 2... 1... REC!) before recording starts.
Provides visual region framing, pulsating countdown ring, and ESC cancellation.
"""

import time
import math
from typing import Optional, Dict
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget, QApplication
from src.config.constants import COLOR_ACCENT, COLOR_DANGER


class CountdownOverlay(QWidget):
    """Translucent overlay displaying an animated pulsing countdown ring and region frame."""

    finished = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)

        self.total_seconds: int = 3
        self.region: Optional[Dict[str, int]] = None
        self._start_time: float = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS animation
        self._anim_timer.timeout.connect(self._on_tick)

    @property
    def is_running(self) -> bool:
        return self._anim_timer.isActive()

    @property
    def current_number(self) -> int:
        if not self.is_running:
            return 0
        elapsed = time.perf_counter() - self._start_time
        remaining = self.total_seconds - elapsed
        return max(1, math.ceil(remaining))

    def start_countdown(self, seconds: int = 3, region: Optional[Dict[str, int]] = None):
        """Begin countdown timer and show overlay."""
        if seconds <= 0:
            self.finished.emit()
            return

        self.total_seconds = max(1, min(10, seconds))
        self.region = region

        # Update geometry to match virtual desktop
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)

        self._start_time = time.perf_counter()
        self.show()
        self.raise_()
        self.activateWindow()
        self._anim_timer.start()
        self.update()

    def cancel(self):
        """Abort countdown."""
        self._anim_timer.stop()
        self.hide()
        self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked on cancel button / outside
            self.cancel()

    def _on_tick(self):
        elapsed = time.perf_counter() - self._start_time
        if elapsed >= self.total_seconds:
            self._anim_timer.stop()
            self.hide()
            self.finished.emit()
            return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark mask
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

        # Determine center and framing area
        if self.region:
            r = QRect(
                self.region.get("left", 0),
                self.region.get("top", 0),
                self.region.get("width", 1920),
                self.region.get("height", 1080),
            )
            # Cutout and highlight region
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(r, Qt.GlobalColor.transparent)

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            border_pen = QPen(QColor(COLOR_ACCENT), 3, Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
            painter.drawRect(r)
            center = r.center()
        else:
            center = self.rect().center()

        elapsed = time.perf_counter() - self._start_time
        remaining = max(0.0, self.total_seconds - elapsed)
        current_second = int(math.ceil(remaining))
        fraction = remaining - math.floor(remaining)  # 1.0 -> 0.0 inside current second

        # Pulse scale calculation
        scale = 0.85 + 0.3 * fraction

        # Center circular badge
        radius = 85
        badge_rect = QRect(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

        # Draw dark glowing background circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(22, 24, 32, 230)))
        painter.drawEllipse(badge_rect)

        # Draw outer progress ring
        ring_pen = QPen(QColor(COLOR_ACCENT), 5, Qt.PenStyle.SolidLine)
        ring_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Arc from 0 to remaining fraction * 360
        progress_angle = int((fraction) * 360 * 16)
        painter.drawArc(badge_rect.adjusted(6, 6, -6, -6), 90 * 16, progress_angle)

        # Draw countdown text or REC
        if current_second > 0:
            text = str(current_second)
            text_color = QColor("#FFFFFF")
        else:
            text = "REC!"
            text_color = QColor(COLOR_DANGER)

        font_size = int(48 * scale)
        painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        painter.setPen(QPen(text_color))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

        # Bottom instruction
        sub_font = QFont("Segoe UI", 10, QFont.Weight.Medium)
        painter.setFont(sub_font)
        painter.setPen(QPen(QColor("#9CA3AF")))
        sub_rect = QRect(center.x() - 120, center.y() + radius + 12, 240, 30)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "Press ESC to Cancel")
