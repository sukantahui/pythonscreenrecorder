"""
Draggable & Resizable Webcam Picture-in-Picture (PiP) floating overlay.
Supports mouse corner/edge drag resizing, mouse wheel resizing, live device switching,
shapes (circle, rounded, rect), horizontal mirroring, and right-click context menu.
"""

import sys
import threading
import time
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPainterPath, QFont, QAction, QCursor
from PyQt6.QtWidgets import QWidget, QApplication, QMenu
import cv2
import numpy as np
from src.config.settings_manager import settings
from src.core.camera_detect import camera_detector


class WebcamPiPOverlay(QWidget):
    """Floating draggable and resizable webcam preview overlay."""

    device_changed = pyqtSignal(int)
    shape_changed = pyqtSignal(str)
    size_changed = pyqtSignal(int)
    closed = pyqtSignal()

    RESIZE_MARGIN = 18

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
        self.pip_size = max(100, min(size, 600))
        self.is_mirrored = mirrored
        self.camera_name = "Camera"

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.pip_size, self.pip_size)
        self.setMouseTracking(True)

        self.current_qimage: Optional[QImage] = None
        self._running = False
        self._is_connecting = True
        self._cap: Optional[cv2.VideoCapture] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._thread_lock = threading.Lock()

        # Dragging & Resizing State
        self.drag_start = QPoint()
        self.is_dragging = False
        self.is_resizing = False
        self.resize_start_pos = QPoint()
        self.resize_start_size = self.pip_size
        self._is_hovered = False

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
        """Resize the PiP overlay smoothly."""
        self.pip_size = max(100, min(size, 600))
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

    def _is_in_resize_zone(self, pos: QPoint) -> bool:
        """Check if mouse position is in bottom-right resize zone or edge perimeter."""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()

        # Bottom-right corner zone
        if x >= w - self.RESIZE_MARGIN and y >= h - self.RESIZE_MARGIN:
            return True

        # Outer edge ring (for circle / rounded shapes)
        if self.shape_type == "circle":
            center_x, center_y = w / 2.0, h / 2.0
            radius = min(w, h) / 2.0
            dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            return radius - self.RESIZE_MARGIN <= dist <= radius + 4

        # For square/rect, bottom or right edges
        return (x >= w - self.RESIZE_MARGIN) or (y >= h - self.RESIZE_MARGIN)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()

    def leaveEvent(self, event):
        self._is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            if self._is_in_resize_zone(pos):
                self.is_resizing = True
                self.is_dragging = False
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_size = self.pip_size
            else:
                self.is_dragging = True
                self.is_resizing = False
                self.drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        global_pos = event.globalPosition().toPoint()

        if self.is_resizing:
            delta_x = global_pos.x() - self.resize_start_pos.x()
            delta_y = global_pos.y() - self.resize_start_pos.y()
            delta = max(delta_x, delta_y)
            new_size = self.resize_start_size + delta
            self.set_size(new_size)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self.is_dragging:
            self.move(global_pos - self.drag_start)
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            # Update hover cursor
            if self._is_in_resize_zone(pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event):
        """Smoothly resize via mouse scroll wheel."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_size(self.pip_size + 16)
        elif delta < 0:
            self.set_size(self.pip_size - 16)

    def _show_context_menu(self, global_pos: QPoint):
        """Context menu for camera switching, shape, size presets, mirror."""
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
        size_menu = menu.addMenu("📏 PiP Size Presets")
        for sz, lbl in [(140, "Compact (140px)"), (220, "Medium (220px)"), (300, "Large (300px)"), (400, "Extra Large (400px)"), (500, "Jumbo (500px)")]:
            act = size_menu.addAction(lbl)
            act.setCheckable(True)
            act.setChecked(abs(self.pip_size - sz) < 25)
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
            path.addRoundedRect(0, 0, self.pip_size, self.pip_size, 26, 26)
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
        border_color = QColor("#818CF8") if self._is_hovered else QColor("#6366F1")
        border_pen = QPen(border_color, 3)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.shape_type == "circle":
            painter.drawEllipse(2, 2, self.pip_size - 4, self.pip_size - 4)
        elif self.shape_type == "rounded":
            painter.drawRoundedRect(2, 2, self.pip_size - 4, self.pip_size - 4, 26, 26)
        else:
            painter.drawRoundedRect(2, 2, self.pip_size - 4, self.pip_size - 4, 8, 8)

        # Draw interactive resize grip indicator in bottom-right corner when hovered
        if self._is_hovered:
            painter.setBrush(QBrush(QColor("#818CF8")))
            painter.setPen(Qt.PenStyle.NoPen)
            br_x = self.pip_size - 18
            br_y = self.pip_size - 18

            # Small 3-dot diagonal grip
            painter.drawEllipse(br_x + 8, br_y + 8, 3, 3)
            painter.drawEllipse(br_x + 8, br_y + 2, 3, 3)
            painter.drawEllipse(br_x + 2, br_y + 8, 3, 3)
