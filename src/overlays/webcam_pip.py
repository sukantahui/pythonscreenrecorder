"""
Draggable Webcam Picture-in-Picture (PiP) floating overlay.
Supports live device switching, shapes (circle, rounded, rect),
dynamic sizing, horizontal mirroring, and right-click context menu.
"""

import sys
import threading
import time
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPainterPath, QFont, QAction
from PyQt6.QtWidgets import QWidget, QApplication, QMenu
import cv2
import numpy as np
from src.config.settings_manager import settings
from src.core.camera_detect import camera_detector


class WebcamPiPOverlay(QWidget):
    """Floating draggable webcam preview overlay."""

    device_changed = pyqtSignal(int)
    shape_changed = pyqtSignal(str)
    size_changed = pyqtSignal(int)
    closed = pyqtSignal()

    def __init__(
        self,
        device_id: int = 0,
        shape: str = "circle",
        size: int = 220,
        mirrored: bool = True
    ):
        super().__init__()
        self.device_id = device_id
        self.shape_type = shape  # "circle", "rounded", "rect"
        self.pip_size = size
        self.is_mirrored = mirrored
        self.camera_name = "Camera"

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.pip_size, self.pip_size)

        self.current_qimage: Optional[QImage] = None
        self._running = False
        self._is_connecting = True
        self._cap: Optional[cv2.VideoCapture] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._thread_lock = threading.Lock()

        self.drag_start = QPoint()
        self.is_dragging = False

        # Refresh timer for UI repaint (~30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def start_webcam(self, device_id: Optional[int] = None) -> bool:
        """Initialize and start the camera stream."""
        if device_id is not None:
            self.device_id = device_id

        self.stop_stream()
        self._is_connecting = True
        self._running = True

        self._capture_thread = threading.Thread(
            target=self._capture_worker,
            args=(self.device_id,),
            daemon=True,
            name=f"WebcamCapture-{self.device_id}"
        )
        self._capture_thread.start()
        self.timer.start(33)
        self.show()
        return True

    def _capture_worker(self, dev_id: int):
        """Worker thread to capture frames from DirectShow/OpenCV."""
        cap = None
        try:
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
            cap = cv2.VideoCapture(dev_id, backend)
            if not cap.isOpened() and backend != 0:
                cap = cv2.VideoCapture(dev_id)

            if not cap.isOpened():
                print(f"[WebcamPiP] Could not open camera device {dev_id}")
                self._is_connecting = False
                return

            with self._thread_lock:
                self._cap = cap
                self._is_connecting = False

            while self._running:
                if not cap.isOpened():
                    time.sleep(0.05)
                    continue

                ret, frame = cap.read()
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
                time.sleep(0.028)  # ~35 FPS capture rate

        except Exception as e:
            print(f"[WebcamPiP] Capture worker error: {e}")
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            with self._thread_lock:
                if self._cap == cap:
                    self._cap = None
            self._is_connecting = False

    def switch_device(self, new_device_id: int):
        """Switch to a new camera device."""
        if self.device_id == new_device_id and self._cap and self._cap.isOpened():
            return
        self.device_id = new_device_id
        settings.set("webcam_device_id", new_device_id)
        self.device_changed.emit(new_device_id)
        self.start_webcam(new_device_id)

    def set_shape(self, shape: str):
        """Set PiP shape: circle, rounded, rect."""
        self.shape_type = shape
        settings.set("webcam_shape", shape)
        self.shape_changed.emit(shape)
        self.update()

    def set_size(self, size: int):
        """Resize the PiP overlay."""
        self.pip_size = max(120, min(size, 480))
        self.setFixedSize(self.pip_size, self.pip_size)
        settings.set("webcam_size", self.pip_size)
        self.size_changed.emit(self.pip_size)
        self.update()

    def set_mirrored(self, mirrored: bool):
        """Toggle mirror mode."""
        self.is_mirrored = mirrored
        settings.set("webcam_mirrored", mirrored)
        self.update()

    def stop_stream(self):
        """Stop background capture stream."""
        self._running = False
        with self._thread_lock:
            if self._cap:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None

    def stop(self):
        """Stop stream and hide overlay."""
        self.stop_stream()
        self.timer.stop()
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def wheelEvent(self, event):
        """Support resizing via mouse scroll wheel."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_size(self.pip_size + 20)
        elif delta < 0:
            self.set_size(self.pip_size - 20)

    def _show_context_menu(self, global_pos: QPoint):
        """Context menu for camera switching, shape, size, mirror."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #161820;
                color: #F9FAFB;
                border: 1px solid #3F4458;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #6366F1;
                color: #FFFFFF;
            }
        """)

        # Camera selector submenu
        cam_menu = menu.addMenu("📷 Select Camera")
        cameras = camera_detector.get_available_cameras()
        for cam in cameras:
            action = cam_menu.addAction(f"{cam['name']} (ID {cam['id']})")
            action.setCheckable(True)
            action.setChecked(cam["id"] == self.device_id)
            cid = cam["id"]
            action.triggered.connect(lambda checked, d_id=cid: self.switch_device(d_id))

        # Shape submenu
        shape_menu = menu.addMenu("🔲 PiP Shape")
        for shp, lbl in [("circle", "Circle"), ("rounded", "Rounded Square"), ("rect", "Square")]:
            act = shape_menu.addAction(lbl)
            act.setCheckable(True)
            act.setChecked(self.shape_type == shp)
            act.triggered.connect(lambda checked, s=shp: self.set_shape(s))

        # Size submenu
        size_menu = menu.addMenu("📏 PiP Size")
        for sz, lbl in [(160, "Small (160px)"), (220, "Medium (220px)"), (280, "Large (280px)"), (340, "Extra Large (340px)")]:
            act = size_menu.addAction(lbl)
            act.setCheckable(True)
            act.setChecked(abs(self.pip_size - sz) < 20)
            act.triggered.connect(lambda checked, s=sz: self.set_size(s))

        # Mirror toggle
        act_mirror = menu.addAction("🪞 Flip Horizontally (Mirror)")
        act_mirror.setCheckable(True)
        act_mirror.setChecked(self.is_mirrored)
        act_mirror.triggered.connect(lambda checked: self.set_mirrored(checked))

        menu.addSeparator()

        act_close = menu.addAction("❌ Hide Webcam PiP")
        act_close.triggered.connect(self.stop)

        menu.exec(global_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        path = QPainterPath()

        if self.shape_type == "circle":
            path.addEllipse(0, 0, self.pip_size, self.pip_size)
        elif self.shape_type == "rounded":
            path.addRoundedRect(0, 0, self.pip_size, self.pip_size, 24, 24)
        else:
            path.addRoundedRect(0, 0, self.pip_size, self.pip_size, 8, 8)

        painter.setClipPath(path)

        if self.current_qimage and not self._is_connecting:
            scaled_img = self.current_qimage.scaled(
                self.pip_size,
                self.pip_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawImage(0, 0, scaled_img)
        else:
            # Placeholder / connecting card
            painter.fillRect(rect, QColor("#161820"))
            painter.setPen(QColor("#9CA3AF"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            msg = "Connecting Cam..." if self._is_connecting else "No Signal"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"📷\n{msg}")

        # Draw glowing outline border
        painter.setClipping(False)
        border_pen = QPen(QColor("#6366F1"), 3)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.shape_type == "circle":
            painter.drawEllipse(2, 2, self.pip_size - 4, self.pip_size - 4)
        elif self.shape_type == "rounded":
            painter.drawRoundedRect(2, 2, self.pip_size - 4, self.pip_size - 4, 24, 24)
        else:
            painter.drawRoundedRect(2, 2, self.pip_size - 4, self.pip_size - 4, 8, 8)
