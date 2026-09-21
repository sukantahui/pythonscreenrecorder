"""
Live keystroke HUD overlay displaying pressed shortcut keys.
"""

import time
from typing import List, Set
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QApplication
from pynput import keyboard


class KeystrokeHUDOverlay(QWidget):
    """Floating transparent badge displaying active keys and combinations."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(320, 60)

        # Position at bottom right corner
        screen_geo = QApplication.primaryScreen().geometry()
        self.move(screen_geo.width() - 350, screen_geo.height() - 120)

        self.current_keys: Set[str] = set()
        self.display_text = ""
        self.last_key_time = 0.0
        self.is_fading = False

        self._key_listener = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_fade)

    def start(self):
        self._key_listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._key_listener.start()
        self.timer.start(50)
        self.show()

    def stop(self):
        self.timer.stop()
        if self._key_listener:
            try:
                self._key_listener.stop()
            except Exception:
                pass
            self._key_listener = None
        self.hide()

    def _format_key(self, key) -> str:
        if isinstance(key, keyboard.Key):
            return key.name.upper()
        elif hasattr(key, "char") and key.char:
            return key.char.upper()
        return str(key)

    def _on_press(self, key):
        key_str = self._format_key(key)
        self.current_keys.add(key_str)
        self.display_text = " + ".join(sorted(self.current_keys))
        self.last_key_time = time.perf_counter()
        self.update()

    def _on_release(self, key):
        key_str = self._format_key(key)
        self.current_keys.discard(key_str)

    def _check_fade(self):
        if self.display_text and (time.perf_counter() - self.last_key_time) > 1.5:
            self.display_text = ""
            self.update()

    def paintEvent(self, event):
        if not self.display_text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw dark capsule container
        painter.setBrush(QColor(22, 24, 32, 220))
        painter.setPen(QColor("#3F4458"))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)

        # Draw key text
        painter.setPen(QColor("#F9FAFB"))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.display_text)
