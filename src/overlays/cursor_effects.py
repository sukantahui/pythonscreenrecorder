"""
Mouse cursor halo and animated click ripple visualizer overlay.
"""

import time
import threading
from typing import List
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor
from PyQt6.QtWidgets import QWidget, QApplication
from pynput import mouse


class ClickRipple:
    """Represents an expanding click animation ring."""

    def __init__(self, x: int, y: int, button_type: str = "left"):
        self.x = x
        self.y = y
        self.button_type = button_type
        self.start_time = time.perf_counter()
        self.duration = 0.4  # seconds
        self.max_radius = 28

        if button_type == "left":
            self.base_color = QColor(239, 68, 68)  # Red
        elif button_type == "right":
            self.base_color = QColor(59, 130, 246)  # Blue
        else:
            self.base_color = QColor(16, 185, 129)  # Green

    def is_alive(self) -> bool:
        return (time.perf_counter() - self.start_time) < self.duration

    def get_progress(self) -> float:
        return min((time.perf_counter() - self.start_time) / self.duration, 1.0)


class CursorEffectsOverlay(QWidget):
    """Transparent full-screen click effects renderer."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput  # Allows clicks to pass through!
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(QApplication.primaryScreen().virtualGeometry())

        self.ripples: List[ClickRipple] = []
        self._mouse_listener = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self):
        self.show()
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()
        self.timer.start(16)  # ~60 FPS animation

    def stop(self):
        self.timer.stop()
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None
        self.hide()

    def _on_click(self, x, y, button, pressed):
        if pressed:
            btn_str = "left" if button == mouse.Button.left else ("right" if button == mouse.Button.right else "middle")
            self.ripples.append(ClickRipple(int(x), int(y), btn_str))

    def _tick(self):
        # Filter alive ripples
        self.ripples = [r for r in self.ripples if r.is_alive()]
        if self.ripples:
            self.update()

    def paintEvent(self, event):
        if not self.ripples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for ripple in self.ripples:
            p = ripple.get_progress()
            radius = int(ripple.max_radius * p)
            alpha = int(255 * (1.0 - p))

            color = QColor(ripple.base_color)
            color.setAlpha(alpha)

            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(ripple.x, ripple.y), radius, radius)
