"""
Draggable Webcam Picture-in-Picture (PiP) floating overlay.
"""

import threading
import time
from typing import Optional
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPainterPath
from PyQt6.QtWidgets import QWidget
import cv2
import numpy as np


class WebcamPiPOverlay(QWidget):
    """Floating draggable webcam preview overlay."""

    def __init__(self, device_id: int = 0, shape: str = "circle", size: int = 220):
        super().__init__()
        self.device_id = device_id
        self.shape_type = shape  # "circle", "rounded", "rect"
        self.pip_size = size
        self.is_mirrored = True

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.pip_size, self.pip_size)

        self.current_qimage: Optional[QImage] = None
        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._capture_thread: Optional[threading.Thread] = None

        self.drag_start = QPoint()
        self.is_dragging = False

        # Refresh timer for UI repaint
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def start_webcam(self) -> bool:
        """Initialize camera stream."""
        try:
            self._cap = cv2.VideoCapture(self.device_id, cv2.CAP_DSHOW if cv2.CAP_DSHOW else 0)
            if not self._cap.isOpened():
                self._cap = cv2.VideoCapture(self.device_id)

            if not self._cap.isOpened():
                print(f"[WebcamPiP] Could not open camera device {self.device_id}")
                return False

            self._running = True
            self._capture_thread = threading.Thread(
                target=self._capture_loop, daemon=True, name="WebcamCaptureThread"
            )
            self._capture_thread.start()
            self.timer.start(33)  # ~30 FPS UI refresh
            self.show()
            return True
        except Exception as e:
            print(f"[WebcamPiP] Error starting webcam: {e}")
            return False

    def _capture_loop(self):
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            if self.is_mirrored:
                frame = cv2.flip(frame, 1)

            # Center crop to square aspect ratio
            h, w, _ = frame.shape
            min_dim = min(h, w)
            start_x = (w - min_dim) // 2
            start_y = (h - min_dim) // 2
            cropped = frame[start_y : start_y + min_dim, start_x : start_x + min_dim]

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * min_dim
            qimg = QImage(
                rgb_frame.data,
                min_dim,
                min_dim,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            ).copy()

            self.current_qimage = qimg
            time.sleep(0.03)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()

        if self.shape_type == "circle":
            path.addEllipse(0, 0, self.pip_size, self.pip_size)
        elif self.shape_type == "rounded":
            path.addRoundedRect(0, 0, self.pip_size, self.pip_size, 20, 20)
        else:
            path.addRect(0, 0, self.pip_size, self.pip_size)

        painter.setClipPath(path)

        if self.current_qimage:
            scaled_img = self.current_qimage.scaled(
                self.pip_size,
                self.pip_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawImage(0, 0, scaled_img)
        else:
            painter.fillRect(rect, QColor("#1E2028"))

        # Draw glowing outline border
        painter.setClipping(False)
        border_pen = QPen(QColor("#6366F1"), 3)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.shape_type == "circle":
            painter.drawEllipse(2, 2, self.pip_size - 4, self.pip_size - 4)
        elif self.shape_type == "rounded":
            painter.drawRoundedRect(2, 2, self.pip_size - 4, self.pip_size - 4, 20, 20)
        else:
            painter.drawRect(2, 2, self.pip_size - 4, self.pip_size - 4)

    def stop(self):
        """Stop camera capture and hide."""
        self._running = False
        self.timer.stop()
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self.hide()
