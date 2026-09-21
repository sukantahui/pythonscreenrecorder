"""
Interactive region selection overlay with 8-handle resizing and dimension HUD.
"""

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton, QHBoxLayout, QLabel, QFrame
from src.config.constants import COLOR_ACCENT, COLOR_DANGER


class RegionSelectorOverlay(QWidget):
    """Fullscreen semi-transparent overlay for selecting a recording region."""

    region_selected = pyqtSignal(dict)  # {"left": x, "top": y, "width": w, "height": h}
    cancelled = pyqtSignal()

    HANDLE_SIZE = 10
    HANDLE_NONE = 0
    HANDLE_TL = 1
    HANDLE_T = 2
    HANDLE_TR = 3
    HANDLE_R = 4
    HANDLE_BR = 5
    HANDLE_B = 6
    HANDLE_BL = 7
    HANDLE_L = 8
    HANDLE_MOVE = 9

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Virtual desktop geometry
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)

        self.selection_rect: QRect = QRect(
            screen_geo.width() // 4,
            screen_geo.height() // 4,
            screen_geo.width() // 2,
            screen_geo.height() // 2,
        )

        self.is_selecting = False
        self.is_resizing = False
        self.current_handle = self.HANDLE_NONE
        self.drag_start_pos = QPoint()
        self.initial_rect = QRect()

        self._setup_hud()

    def _setup_hud(self):
        """Create floating control bar inside the overlay."""
        self.hud_frame = QFrame(self)
        self.hud_frame.setStyleSheet("""
            QFrame {
                background-color: #161820;
                border: 1px solid #3F4458;
                border-radius: 8px;
                padding: 4px;
            }
            QLabel {
                color: #F9FAFB;
                font-size: 12px;
                font-weight: bold;
                padding: 0 8px;
            }
            QPushButton {
                background-color: #20232E;
                color: #F9FAFB;
                border: 1px solid #2D313F;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2B2F3D;
                border-color: #6366F1;
            }
            QPushButton#BtnConfirm {
                background-color: #EF4444;
                border-color: #DC2626;
                color: white;
                font-weight: bold;
            }
            QPushButton#BtnConfirm:hover {
                background-color: #DC2626;
            }
        """)

        layout = QHBoxLayout(self.hud_frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.lbl_dims = QLabel("1920 × 1080 (16:9)", self.hud_frame)
        layout.addWidget(self.lbl_dims)

        btn_1080p = QPushButton("1080p", self.hud_frame)
        btn_1080p.clicked.connect(lambda: self._set_preset(1920, 1080))
        layout.addWidget(btn_1080p)

        btn_720p = QPushButton("720p", self.hud_frame)
        btn_720p.clicked.connect(lambda: self._set_preset(1280, 720))
        layout.addWidget(btn_720p)

        btn_vertical = QPushButton("9:16 (Shorts)", self.hud_frame)
        btn_vertical.clicked.connect(lambda: self._set_preset(1080, 1920))
        layout.addWidget(btn_vertical)

        btn_full = QPushButton("Fullscreen", self.hud_frame)
        btn_full.clicked.connect(self._set_fullscreen)
        layout.addWidget(btn_full)

        btn_cancel = QPushButton("✕ Cancel", self.hud_frame)
        btn_cancel.clicked.connect(self._cancel)
        layout.addWidget(btn_cancel)

        btn_confirm = QPushButton("✔ Confirm", self.hud_frame)
        btn_confirm.setObjectName("BtnConfirm")
        btn_confirm.clicked.connect(self._confirm)
        layout.addWidget(btn_confirm)

        self._update_hud_position()

    def _set_preset(self, w: int, h: int):
        cx = self.selection_rect.center().x()
        cy = self.selection_rect.center().y()
        self.selection_rect = QRect(cx - w // 2, cy - h // 2, w, h)
        self._normalize_and_update()

    def _set_fullscreen(self):
        geo = QApplication.primaryScreen().virtualGeometry()
        self.selection_rect = QRect(0, 0, geo.width(), geo.height())
        self._normalize_and_update()

    def _update_hud_position(self):
        w = self.selection_rect.width()
        h = self.selection_rect.height()
        self.lbl_dims.setText(f"{w} × {h}")

        self.hud_frame.adjustSize()
        hud_w = self.hud_frame.width()
        hud_h = self.hud_frame.height()

        # Place HUD below selection rect, or above if near bottom of screen
        hud_x = self.selection_rect.center().x() - hud_w // 2
        hud_y = self.selection_rect.bottom() + 10

        if hud_y + hud_h > self.height():
            hud_y = self.selection_rect.top() - hud_h - 10

        hud_x = max(10, min(hud_x, self.width() - hud_w - 10))
        hud_y = max(10, min(hud_y, self.height() - hud_h - 10))

        self.hud_frame.move(hud_x, hud_y)
        self.hud_frame.show()

    def _normalize_and_update(self):
        self.selection_rect = self.selection_rect.normalized()
        self._update_hud_position()
        self.update()

    def _confirm(self):
        norm = self.selection_rect.normalized()
        # Even dimension enforcement
        w = norm.width() - (norm.width() % 2)
        h = norm.height() - (norm.height() % 2)
        region = {
            "left": norm.left(),
            "top": norm.top(),
            "width": max(64, w),
            "height": max(64, h),
        }
        self.hide()
        self.region_selected.emit(region)

    def _cancel(self):
        self.hide()
        self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._confirm()
        super().keyPressEvent(event)

    def _get_handle_at(self, pos: QPoint) -> int:
        r = self.selection_rect.normalized()
        hs = self.HANDLE_SIZE

        handles = {
            self.HANDLE_TL: QRect(r.left() - hs, r.top() - hs, hs * 2, hs * 2),
            self.HANDLE_TR: QRect(r.right() - hs, r.top() - hs, hs * 2, hs * 2),
            self.HANDLE_BL: QRect(r.left() - hs, r.bottom() - hs, hs * 2, hs * 2),
            self.HANDLE_BR: QRect(r.right() - hs, r.bottom() - hs, hs * 2, hs * 2),
            self.HANDLE_T: QRect(r.center().x() - hs, r.top() - hs, hs * 2, hs * 2),
            self.HANDLE_B: QRect(r.center().x() - hs, r.bottom() - hs, hs * 2, hs * 2),
            self.HANDLE_L: QRect(r.left() - hs, r.center().y() - hs, hs * 2, hs * 2),
            self.HANDLE_R: QRect(r.right() - hs, r.center().y() - hs, hs * 2, hs * 2),
        }

        for handle, rect in handles.items():
            if rect.contains(pos):
                return handle

        if r.contains(pos):
            return self.HANDLE_MOVE

        return self.HANDLE_NONE

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handle = self._get_handle_at(pos)
            if handle != self.HANDLE_NONE:
                self.is_resizing = True
                self.current_handle = handle
                self.drag_start_pos = pos
                self.initial_rect = QRect(self.selection_rect)
            else:
                self.is_selecting = True
                self.drag_start_pos = pos
                self.selection_rect = QRect(pos, pos)
            self._normalize_and_update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.is_selecting:
            self.selection_rect = QRect(self.drag_start_pos, pos)
            self._normalize_and_update()
        elif self.is_resizing:
            diff = pos - self.drag_start_pos
            r = QRect(self.initial_rect)

            if self.current_handle == self.HANDLE_MOVE:
                r.translate(diff)
            elif self.current_handle == self.HANDLE_TL:
                r.setTopLeft(r.topLeft() + diff)
            elif self.current_handle == self.HANDLE_TR:
                r.setTopRight(r.topRight() + diff)
            elif self.current_handle == self.HANDLE_BL:
                r.setBottomLeft(r.bottomLeft() + diff)
            elif self.current_handle == self.HANDLE_BR:
                r.setBottomRight(r.bottomRight() + diff)
            elif self.current_handle == self.HANDLE_T:
                r.setTop(r.top() + diff.y())
            elif self.current_handle == self.HANDLE_B:
                r.setBottom(r.bottom() + diff.y())
            elif self.current_handle == self.HANDLE_L:
                r.setLeft(r.left() + diff.x())
            elif self.current_handle == self.HANDLE_R:
                r.setRight(r.right() + diff.x())

            self.selection_rect = r
            self._normalize_and_update()
        else:
            # Update cursor shape based on hover handle
            handle = self._get_handle_at(pos)
            cursors = {
                self.HANDLE_TL: Qt.CursorShape.SizeFDiagCursor,
                self.HANDLE_BR: Qt.CursorShape.SizeFDiagCursor,
                self.HANDLE_TR: Qt.CursorShape.SizeBDiagCursor,
                self.HANDLE_BL: Qt.CursorShape.SizeBDiagCursor,
                self.HANDLE_T: Qt.CursorShape.SizeVerCursor,
                self.HANDLE_B: Qt.CursorShape.SizeVerCursor,
                self.HANDLE_L: Qt.CursorShape.SizeHorCursor,
                self.HANDLE_R: Qt.CursorShape.SizeHorCursor,
                self.HANDLE_MOVE: Qt.CursorShape.SizeAllCursor,
                self.HANDLE_NONE: Qt.CursorShape.CrossCursor,
            }
            self.setCursor(cursors.get(handle, Qt.CursorShape.CrossCursor))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = False
            self.is_resizing = False
            self.current_handle = self.HANDLE_NONE
            self._normalize_and_update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark overlay mask
        mask_color = QColor(0, 0, 0, 140)
        painter.fillRect(self.rect(), mask_color)

        # Clear the cutout selected area
        r = self.selection_rect.normalized()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(r, Qt.GlobalColor.transparent)

        # Draw glowing bounding border around selection
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        border_pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)
        painter.drawRect(r)

        # Draw 8 resize handles
        handle_brush = QBrush(QColor("#FFFFFF"))
        painter.setBrush(handle_brush)
        painter.setPen(QPen(QColor(COLOR_ACCENT), 1.5))
        hs = self.HANDLE_SIZE

        handle_points = [
            r.topLeft(),
            QPoint(r.center().x(), r.top()),
            r.topRight(),
            QPoint(r.right(), r.center().y()),
            r.bottomRight(),
            QPoint(r.center().x(), r.bottom()),
            r.bottomLeft(),
            QPoint(r.left(), r.center().y()),
        ]

        for p in handle_points:
            painter.drawRect(p.x() - hs // 2, p.y() - hs // 2, hs, hs)
