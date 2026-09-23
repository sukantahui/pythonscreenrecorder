"""
Studio-Grade Draggable & Resizable Webcam Picture-in-Picture (PiP) Overlay.
Supports Full HD 1080p capture, Presenter Fullscreen/Region Mode (covers whole recording area),
dynamic aspect-ratio framing (16:9 Widescreen, Circle Bubble, Rounded Card, 9:16 Vertical Reel,
Classic Square), real-time studio lighting & color grading filters, 1-click corner docking,
customizable border themes, on-hover quick-action pill toolbar, and smooth resizing.
"""

import sys
import threading
import time
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QImage,
    QPainterPath,
    QFont,
    QAction,
    QCursor,
)
from PyQt6.QtWidgets import QWidget, QApplication, QMenu
import cv2
import numpy as np

from src.config.settings_manager import settings
from src.config.constants import (
    WEBCAM_SHAPES,
    WEBCAM_FILTERS,
    WEBCAM_BORDER_THEMES,
)
from src.core.camera_detect import camera_detector


class WebcamPiPOverlay(QWidget):
    """Studio-grade floating draggable, resizable, and fullscreen presenter webcam overlay."""

    device_changed = pyqtSignal(int)
    shape_changed = pyqtSignal(str)
    size_changed = pyqtSignal(int)
    filter_changed = pyqtSignal(str)
    border_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(bool)  # True = Fullscreen/Region, False = PiP
    closed = pyqtSignal()

    RESIZE_MARGIN = 20

    def __init__(
        self,
        device_id: int = 0,
        shape: str = "wide",
        size: int = 220,
        mirrored: bool = True,
        filter_name: str = "normal",
        border_theme: str = "indigo",
    ):
        super().__init__()
        self.device_id = device_id
        self.shape_type = shape if shape in WEBCAM_SHAPES else "circle"
        self.pip_size = max(100, min(size, 600))
        self.is_mirrored = mirrored
        self.filter_type = filter_name if filter_name in WEBCAM_FILTERS else "normal"
        self.border_theme = border_theme if border_theme in WEBCAM_BORDER_THEMES else "indigo"

        # Fullscreen / Presenter Mode state
        self.is_fullscreen_cam = False
        self._saved_pip_geometry: Optional[QRect] = None
        self._saved_pip_size: int = self.pip_size
        self._saved_pip_shape: str = self.shape_type
        self.recording_region: Optional[Dict[str, int]] = None

        # Corner docking index for quick cycling
        self._corners = ["bottom-right", "bottom-left", "top-right", "top-left"]
        self._current_corner_idx = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        w, h = self._get_pip_dimensions()
        self.setFixedSize(w, h)

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

        # Quick-action pill button bounding boxes
        self._action_rects: Dict[str, QRect] = {}

        # Refresh timer for UI repaint (~30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def set_recording_region(self, region: Optional[Dict[str, int]]):
        """Store target recording region for fullscreen presenter mode."""
        self.recording_region = region
        if self.is_fullscreen_cam:
            if region:
                self.setFixedSize(region["width"], region["height"])
                self.move(region["left"], region["top"])
            else:
                screen = QApplication.primaryScreen()
                geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
                self.setFixedSize(geo.width(), geo.height())
                self.move(geo.left(), geo.top())

    def toggle_fullscreen_cam(self, target_region: Optional[Dict[str, int]] = None):
        """Toggle between Fullscreen/Region Presenter Mode and Floating PiP Mode."""
        if not self.is_fullscreen_cam:
            # Switch to Fullscreen / Region Presenter Mode
            self._saved_pip_geometry = self.geometry()
            self._saved_pip_size = self.pip_size
            self._saved_pip_shape = self.shape_type

            r = target_region or self.recording_region
            if r:
                x, y, w, h = r["left"], r["top"], r["width"], r["height"]
            else:
                screen = QApplication.primaryScreen()
                geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
                x, y, w, h = geo.left(), geo.top(), geo.width(), geo.height()

            self.is_fullscreen_cam = True
            self.setFixedSize(w, h)
            self.move(x, y)
            self.mode_changed.emit(True)
            self.update()
        else:
            # Restore to Floating PiP Mode
            self.is_fullscreen_cam = False
            self.set_shape(self._saved_pip_shape)
            self.set_size(self._saved_pip_size)
            if self._saved_pip_geometry:
                self.move(self._saved_pip_geometry.topLeft())
            else:
                self.snap_to_corner("bottom-right")
            self.mode_changed.emit(False)
            self.update()

    def _get_pip_dimensions(self) -> Tuple[int, int]:
        """Compute pixel width & height from shape aspect ratio and base size."""
        if self.is_fullscreen_cam:
            return (self.width(), self.height())

        base = self.pip_size
        if self.shape_type == "wide":
            return (int(base * 16 / 9), base)
        elif self.shape_type == "portrait":
            return (base, int(base * 16 / 9))
        else:  # circle, rounded, square
            return (base, base)

    def start_webcam(self, device_id: Optional[int] = None) -> bool:
        """Initialize and start the camera stream with Full HD 1080p resolution."""
        if device_id is not None:
            self.device_id = device_id

        self.stop_stream()
        self._is_connecting = True
        self._running = True

        self._capture_thread = threading.Thread(
            target=self._capture_worker,
            args=(self.device_id,),
            daemon=True,
            name=f"WebcamCapture-{self.device_id}",
        )
        self._capture_thread.start()
        self.timer.start(33)
        self.show()
        return True

    def _apply_filter(self, frame: np.ndarray) -> np.ndarray:
        """Apply real-time studio lighting & color grading filter."""
        f_type = self.filter_type
        if f_type == "normal" or frame is None:
            return frame

        try:
            if f_type == "warm":
                arr = frame.astype(np.float32)
                arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.12 + 10, 0, 255)
                arr[:, :, 1] = np.clip(arr[:, :, 1] * 1.04, 0, 255)
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 0.92, 0, 255)
                return arr.astype(np.uint8)

            elif f_type == "cool":
                arr = frame.astype(np.float32)
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.15 + 10, 0, 255)
                arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.92, 0, 255)
                return arr.astype(np.uint8)

            elif f_type == "bright":
                return cv2.convertScaleAbs(frame, alpha=1.15, beta=25)

            elif f_type == "bw":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            elif f_type == "beauty":
                return cv2.bilateralFilter(frame, d=7, sigmaColor=40, sigmaSpace=40)

        except Exception as e:
            print(f"[WebcamPiP] Filter {f_type} error: {e}")

        return frame

    def _capture_worker(self, dev_id: int):
        """Worker thread to capture frames from DirectShow/OpenCV in Full HD."""
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

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_FPS, 30)

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

                frame = self._apply_filter(frame)

                target_w, target_h = self._get_pip_dimensions()
                target_w = max(64, target_w)
                target_h = max(64, target_h)
                target_aspect = target_w / target_h

                h, w, _ = frame.shape
                current_aspect = w / max(1, h)

                if current_aspect > target_aspect:
                    crop_w = int(h * target_aspect)
                    crop_h = h
                    start_x = (w - crop_w) // 2
                    start_y = 0
                else:
                    crop_w = w
                    crop_h = int(w / target_aspect)
                    start_x = 0
                    start_y = (h - crop_h) // 2

                cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]

                if crop_w != target_w or crop_h != target_h:
                    cropped = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

                rgb_frame = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                bytes_per_line = 3 * target_w
                qimg = QImage(
                    rgb_frame.data,
                    target_w,
                    target_h,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                ).copy()

                self.current_qimage = qimg
                time.sleep(0.028)

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
        """Set PiP shape: wide (16:9), circle, rounded, portrait (9:16), square."""
        if shape == "rect":
            shape = "wide"
        if shape not in WEBCAM_SHAPES:
            shape = "wide"
        self.shape_type = shape
        if not self.is_fullscreen_cam:
            w, h = self._get_pip_dimensions()
            self.setFixedSize(w, h)
        settings.set("webcam_shape", shape)
        self.shape_changed.emit(shape)
        self.update()

    def set_filter(self, filter_name: str):
        """Set active studio lighting/color filter."""
        if filter_name in WEBCAM_FILTERS:
            self.filter_type = filter_name
            settings.set("webcam_filter", filter_name)
            self.filter_changed.emit(filter_name)
            self.update()

    def set_border_theme(self, theme_name: str):
        """Set active border color theme."""
        if theme_name in WEBCAM_BORDER_THEMES:
            self.border_theme = theme_name
            settings.set("webcam_border_color", theme_name)
            self.border_changed.emit(theme_name)
            self.update()

    def set_size(self, size: int):
        """Resize the PiP overlay smoothly."""
        self.pip_size = max(100, min(size, 600))
        if not self.is_fullscreen_cam:
            w, h = self._get_pip_dimensions()
            self.setFixedSize(w, h)
        settings.set("webcam_size", self.pip_size)
        self.size_changed.emit(self.pip_size)
        self.update()

    def set_mirrored(self, mirrored: bool):
        """Toggle mirror mode."""
        self.is_mirrored = mirrored
        settings.set("webcam_mirrored", mirrored)
        self.update()

    def snap_to_corner(self, corner: str = "bottom-right"):
        """1-Click dock the PiP to any screen corner."""
        if self.is_fullscreen_cam:
            self.toggle_fullscreen_cam()

        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        margin_x, margin_y = 24, 24

        if corner == "bottom-right":
            x = geo.right() - w - margin_x
            y = geo.bottom() - h - margin_y
        elif corner == "bottom-left":
            x = geo.left() + margin_x
            y = geo.bottom() - h - margin_y
        elif corner == "top-right":
            x = geo.right() - w - margin_x
            y = geo.top() + margin_y
        elif corner == "top-left":
            x = geo.left() + margin_x
            y = geo.top() + margin_y
        else:
            return

        self.move(max(geo.left(), x), max(geo.top(), y))

    def cycle_shape(self):
        """Cycle through available PiP shapes."""
        if self.is_fullscreen_cam:
            self.toggle_fullscreen_cam()
        shape_keys = list(WEBCAM_SHAPES.keys())
        try:
            curr_idx = shape_keys.index(self.shape_type)
            next_shape = shape_keys[(curr_idx + 1) % len(shape_keys)]
        except ValueError:
            next_shape = "wide"
        self.set_shape(next_shape)

    def cycle_filter(self):
        """Cycle through studio lighting & color filters."""
        filter_keys = list(WEBCAM_FILTERS.keys())
        try:
            curr_idx = filter_keys.index(self.filter_type)
            next_filter = filter_keys[(curr_idx + 1) % len(filter_keys)]
        except ValueError:
            next_filter = "normal"
        self.set_filter(next_filter)

    def cycle_corner(self):
        """Cycle docking position across screen corners."""
        self._current_corner_idx = (self._current_corner_idx + 1) % len(self._corners)
        self.snap_to_corner(self._corners[self._current_corner_idx])

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

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.is_fullscreen_cam:
            self.toggle_fullscreen_cam()
        super().keyPressEvent(event)

    def _is_in_resize_zone(self, pos: QPoint) -> bool:
        """Check if mouse position is in bottom-right resize zone."""
        if self.is_fullscreen_cam:
            return False

        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()

        if x >= w - self.RESIZE_MARGIN and y >= h - self.RESIZE_MARGIN:
            return True

        if self.shape_type == "circle":
            center_x, center_y = w / 2.0, h / 2.0
            radius = min(w, h) / 2.0
            dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            return radius - self.RESIZE_MARGIN <= dist <= radius + 4

        return (x >= w - self.RESIZE_MARGIN) or (y >= h - self.RESIZE_MARGIN)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()

    def leaveEvent(self, event):
        self._is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        global_pos = event.globalPosition().toPoint()

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked inside hover quick-action pill buttons
            if self._is_hovered:
                for action, rect in self._action_rects.items():
                    if rect.contains(pos):
                        if action == "mode":
                            self.toggle_fullscreen_cam()
                        elif action == "shape":
                            self.cycle_shape()
                        elif action == "filter":
                            self.cycle_filter()
                        elif action == "mirror":
                            self.set_mirrored(not self.is_mirrored)
                        elif action == "snap":
                            self.cycle_corner()
                        elif action == "close":
                            self.stop()
                        return

            if not self.is_fullscreen_cam:
                if self._is_in_resize_zone(pos):
                    self.is_resizing = True
                    self.is_dragging = False
                    self.resize_start_pos = global_pos
                    self.resize_start_size = self.pip_size
                else:
                    self.is_dragging = True
                    self.is_resizing = False
                    self.drag_start = global_pos - self.frameGeometry().topLeft()

        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(global_pos)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        global_pos = event.globalPosition().toPoint()

        if not self.is_fullscreen_cam and self.is_resizing:
            delta_x = global_pos.x() - self.resize_start_pos.x()
            delta_y = global_pos.y() - self.resize_start_pos.y()
            delta = max(delta_x, delta_y)
            new_size = self.resize_start_size + delta
            self.set_size(new_size)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif not self.is_fullscreen_cam and self.is_dragging:
            self.move(global_pos - self.drag_start)
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            in_action_btn = any(rect.contains(pos) for rect in self._action_rects.values()) if self._is_hovered else False
            if in_action_btn:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif not self.is_fullscreen_cam and self._is_in_resize_zone(pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event):
        """Smoothly resize via mouse scroll wheel in PiP mode."""
        if self.is_fullscreen_cam:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_size(self.pip_size + 16)
        elif delta < 0:
            self.set_size(self.pip_size - 16)

    def _show_context_menu(self, global_pos: QPoint):
        """Context menu for mode toggle, camera, shapes, filters, border themes, docking, sizing."""
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

        # 1. Mode Switcher (Presenter Fullscreen ↔ Floating PiP)
        if self.is_fullscreen_cam:
            act_mode = menu.addAction("🗗 Restore Floating PiP Mode (Esc)")
        else:
            act_mode = menu.addAction("⛶ Presenter Mode (Cover Recording Area)")
        act_mode.triggered.connect(lambda: self.toggle_fullscreen_cam())

        menu.addSeparator()

        # 2. Camera selector submenu
        cam_menu = menu.addMenu("📷 Select Camera")
        cameras = camera_detector.get_available_cameras()
        for cam in cameras:
            action = cam_menu.addAction(f"{cam['name']} (ID {cam['id']})")
            action.setCheckable(True)
            action.setChecked(cam["id"] == self.device_id)
            cid = cam["id"]
            action.triggered.connect(lambda checked, d_id=cid: self.switch_device(d_id))

        # 3. Shape submenu
        shape_menu = menu.addMenu("🔲 Framing & Shape")
        for shp, info in WEBCAM_SHAPES.items():
            act = shape_menu.addAction(f"{info['icon']} {info['name']}")
            act.setCheckable(True)
            act.setChecked(self.shape_type == shp and not self.is_fullscreen_cam)
            act.triggered.connect(lambda checked, s=shp: self.set_shape(s))

        # 4. Lighting & Filters submenu
        filter_menu = menu.addMenu("☀️ Studio Lighting & Filters")
        for f_key, info in WEBCAM_FILTERS.items():
            act = filter_menu.addAction(f"{info['icon']} {info['name']}")
            act.setCheckable(True)
            act.setChecked(self.filter_type == f_key)
            act.triggered.connect(lambda checked, f=f_key: self.set_filter(f))

        # 5. Border Theme submenu
        border_menu = menu.addMenu("🎨 Border Theme")
        for b_key, info in WEBCAM_BORDER_THEMES.items():
            act = border_menu.addAction(info["name"])
            act.setCheckable(True)
            act.setChecked(self.border_theme == b_key)
            act.triggered.connect(lambda checked, b=b_key: self.set_border_theme(b))

        # 6. Snap to Corner submenu
        dock_menu = menu.addMenu("📍 Dock to Corner")
        for c_key, c_name in [
            ("bottom-right", "↘️ Bottom-Right (Default)"),
            ("bottom-left", "↙️ Bottom-Left"),
            ("top-right", "↗️ Top-Right"),
            ("top-left", "↖️ Top-Left"),
        ]:
            act = dock_menu.addAction(c_name)
            act.triggered.connect(lambda checked, c=c_key: self.snap_to_corner(c))

        # 7. Size presets submenu
        size_menu = menu.addMenu("📏 Size Presets")
        for sz, lbl in [
            (140, "Compact (140px)"),
            (220, "Medium (220px)"),
            (320, "Large (320px)"),
            (420, "Extra Large (420px)"),
            (520, "Jumbo (520px)"),
        ]:
            act = size_menu.addAction(lbl)
            act.setCheckable(True)
            act.setChecked(abs(self.pip_size - sz) < 25 and not self.is_fullscreen_cam)
            act.triggered.connect(lambda checked, s=sz: self.set_size(s))

        # 8. Mirror toggle
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

        w, h = self.width(), self.height()
        rect = self.rect()
        path = QPainterPath()

        if self.is_fullscreen_cam:
            path.addRect(0, 0, w, h)
        elif self.shape_type == "circle":
            path.addEllipse(0, 0, w, h)
        elif self.shape_type == "rounded":
            path.addRoundedRect(0, 0, w, h, 26, 26)
        elif self.shape_type == "wide":
            path.addRoundedRect(0, 0, w, h, 14, 14)
        elif self.shape_type == "portrait":
            path.addRoundedRect(0, 0, w, h, 16, 16)
        else:  # square
            path.addRoundedRect(0, 0, w, h, 10, 10)

        # 1. Paint Camera Image clipped to shape
        painter.setClipPath(path)
        if self.current_qimage and not self._is_connecting:
            painter.drawImage(rect, self.current_qimage)
        else:
            painter.fillRect(rect, QColor("#161820"))
            painter.setPen(QColor("#9CA3AF"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            msg = "Connecting 1080p Cam..." if self._is_connecting else "No Signal"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"📷\n{msg}")

        painter.setClipping(False)

        # 2. Draw Theme Border / Glowing Ring (if not in full presenter mode)
        theme_info = WEBCAM_BORDER_THEMES.get(self.border_theme, WEBCAM_BORDER_THEMES["indigo"])
        color_str = theme_info["glow"] if self._is_hovered else theme_info["color"]

        if not self.is_fullscreen_cam and color_str != "transparent":
            border_color = QColor(color_str)
            border_pen = QPen(border_color, 3)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if self.shape_type == "circle":
                painter.drawEllipse(2, 2, w - 4, h - 4)
            elif self.shape_type == "rounded":
                painter.drawRoundedRect(2, 2, w - 4, h - 4, 26, 26)
            elif self.shape_type == "wide":
                painter.drawRoundedRect(2, 2, w - 4, h - 4, 14, 14)
            elif self.shape_type == "portrait":
                painter.drawRoundedRect(2, 2, w - 4, h - 4, 16, 16)
            else:
                painter.drawRoundedRect(2, 2, w - 4, h - 4, 10, 10)

        # 3. Draw Hover Controls: Quick-Action Pill Toolbar + Resize Grip
        if self._is_hovered:
            if not self.is_fullscreen_cam:
                painter.setBrush(QBrush(QColor(theme_info.get("glow", "#818CF8"))))
                painter.setPen(Qt.PenStyle.NoPen)
                br_x = w - 18
                br_y = h - 18
                painter.drawEllipse(br_x + 8, br_y + 8, 3, 3)
                painter.drawEllipse(br_x + 8, br_y + 2, 3, 3)
                painter.drawEllipse(br_x + 2, br_y + 8, 3, 3)

            # Frosted Action Pill Toolbar at top center (placed high at top edge to keep face/eyes clear)
            if self.is_fullscreen_cam:
                actions = [
                    ("mode", "🗗", "Restore PiP (Esc)"),
                    ("filter", "☀️", "Cycle Filter"),
                    ("mirror", "🪞", "Flip Mirror"),
                    ("close", "✕", "Hide Cam"),
                ]
                btn_w = 30
                pill_h = 24
                pill_y = 6
                font_size = 9
            else:
                actions = [
                    ("mode", "⛶", "Full Recording Area"),
                    ("shape", "🔲", "Cycle Shape"),
                    ("filter", "☀️", "Cycle Filter"),
                    ("mirror", "🪞", "Flip Mirror"),
                    ("snap", "📍", "Dock Corner"),
                    ("close", "✕", "Close"),
                ]
                btn_w = 26
                pill_h = 22
                pill_y = 2 if self.shape_type == "circle" else 3
                font_size = 9

            pill_w = len(actions) * btn_w + 10
            pill_x = (w - pill_w) // 2

            pill_rect = QRect(pill_x, pill_y, pill_w, pill_h)
            painter.setBrush(QBrush(QColor(16, 18, 24, 235)))
            painter.setPen(QPen(QColor(63, 68, 88, 200), 1))
            painter.drawRoundedRect(pill_rect, pill_h // 2, pill_h // 2)

            painter.setFont(QFont("Segoe UI Emoji", font_size))
            self._action_rects.clear()

            for i, (act_key, icon, _) in enumerate(actions):
                btn_x = pill_x + 5 + (i * btn_w)
                btn_rect = QRect(btn_x, pill_y + 1, btn_w, pill_h - 2)
                self._action_rects[act_key] = btn_rect

                mouse_p = self.mapFromGlobal(QCursor.pos())
                if btn_rect.contains(mouse_p):
                    painter.setBrush(QBrush(QColor(99, 102, 241, 180)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(btn_rect, 4, 4)

                painter.setPen(QColor("#F9FAFB"))
                painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, icon)
