"""
Interactive region selection overlay with 8-handle resizing, locked aspect ratio presets,
rule-of-thirds composition grid, and a modern floating HUD.
"""

from typing import Optional, Tuple, Dict
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor
from PyQt6.QtWidgets import (
    QWidget, QApplication, QPushButton, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QComboBox
)
from src.config.constants import COLOR_ACCENT, COLOR_DANGER, ASPECT_RATIO_PRESETS


class RegionSelectorOverlay(QWidget):
    """Fullscreen semi-transparent overlay for selecting a recording region with locked aspect ratios."""

    region_selected = pyqtSignal(dict)  # {"left": x, "top": y, "width": w, "height": h, "ratio_key": k, "ratio_name": n}
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
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Virtual desktop geometry
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)

        self.current_ratio_key: str = "freeform"
        self.is_ratio_locked: bool = False
        self.custom_locked_ratio: Optional[float] = None
        self.show_grid: bool = True

        # Default selection: centered 16:9
        def_w = min(1920, int(screen_geo.width() * 0.7))
        def_w -= def_w % 2
        def_h = int(def_w * 9 / 16)
        def_h -= def_h % 2

        self.selection_rect: QRect = QRect(
            screen_geo.center().x() - def_w // 2,
            screen_geo.center().y() - def_h // 2,
            def_w,
            def_h,
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
                background-color: #13151D;
                border: 1px solid #32374A;
                border-radius: 9px;
                padding: 4px;
            }
            QLabel {
                color: #F9FAFB;
                font-size: 11px;
                font-weight: bold;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #1E2230;
                color: #F3F4F6;
                border: 1px solid #2D3345;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
                min-width: 140px;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1D27;
                color: #F9FAFB;
                border: 1px solid #3F4458;
                selection-background-color: #6366F1;
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton {
                background-color: #1E2230;
                color: #F3F4F6;
                border: 1px solid #2D3345;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #282D40;
                border-color: #6366F1;
            }
            QPushButton:checked {
                background-color: #4F46E5;
                border-color: #6366F1;
                color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton#BtnConfirm {
                background-color: #059669;
                border-color: #047857;
                color: white;
                font-weight: bold;
                padding: 5px 14px;
            }
            QPushButton#BtnConfirm:hover {
                background-color: #10B981;
            }
            QPushButton#BtnCancel {
                background-color: #2D3345;
                color: #E5E7EB;
            }
            QPushButton#BtnCancel:hover {
                background-color: #DC2626;
                color: white;
            }
        """)

        layout = QHBoxLayout(self.hud_frame)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)

        # 1. Aspect Ratio Selector
        self.combo_ratio = QComboBox(self.hud_frame)
        self.combo_ratio.setToolTip("Preset social media & video aspect ratio")
        for key, info in ASPECT_RATIO_PRESETS.items():
            self.combo_ratio.addItem(f"{info['icon']} {info['name']}", key)
        self.combo_ratio.currentIndexChanged.connect(self._on_ratio_combo_changed)
        layout.addWidget(self.combo_ratio)

        # 2. Lock Ratio Toggle
        self.btn_lock = QPushButton("🔓 Free", self.hud_frame)
        self.btn_lock.setCheckable(True)
        self.btn_lock.setToolTip("Lock aspect ratio during resizing and dragging")
        self.btn_lock.toggled.connect(self._toggle_lock)
        layout.addWidget(self.btn_lock)

        # 3. Size / Resolution Presets ComboBox
        self.combo_size = QComboBox(self.hud_frame)
        self.combo_size.setToolTip("Quick standard resolution for active ratio")
        self.combo_size.setMinimumWidth(110)
        self.combo_size.currentIndexChanged.connect(self._on_size_combo_changed)
        layout.addWidget(self.combo_size)

        # 4. Center Button
        btn_center = QPushButton("🎯 Center", self.hud_frame)
        btn_center.setToolTip("Center selection on current screen")
        btn_center.clicked.connect(self._center_selection)
        layout.addWidget(btn_center)

        # 5. Rule of Thirds Grid Toggle
        self.btn_grid = QPushButton("📐 Grid", self.hud_frame)
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.setToolTip("Toggle Rule-of-Thirds framing guides")
        self.btn_grid.toggled.connect(self._toggle_grid)
        layout.addWidget(self.btn_grid)

        # 6. Fullscreen
        btn_full = QPushButton("🖥️ Full", self.hud_frame)
        btn_full.setToolTip("Fill entire screen")
        btn_full.clicked.connect(self._set_fullscreen)
        layout.addWidget(btn_full)

        # 7. Live Dimensions Label
        self.lbl_dims = QLabel("1920 × 1080", self.hud_frame)
        self.lbl_dims.setStyleSheet("color: #A5B4FC; font-weight: bold; padding: 0 4px;")
        layout.addWidget(self.lbl_dims)

        # 8. Cancel & Confirm
        btn_cancel = QPushButton("✕ Cancel", self.hud_frame)
        btn_cancel.setObjectName("BtnCancel")
        btn_cancel.clicked.connect(self._cancel)
        layout.addWidget(btn_cancel)

        btn_confirm = QPushButton("✔ Confirm", self.hud_frame)
        btn_confirm.setObjectName("BtnConfirm")
        btn_confirm.clicked.connect(self._confirm)
        layout.addWidget(btn_confirm)

        self._populate_size_combo("freeform")
        self._update_hud_position()

    def get_active_ratio(self) -> Optional[float]:
        """Return the locked aspect ratio float (w / h) or None if unlocked."""
        if not self.is_ratio_locked:
            return None
        if self.current_ratio_key in ASPECT_RATIO_PRESETS:
            r = ASPECT_RATIO_PRESETS[self.current_ratio_key].get("ratio")
            if r is not None and len(r) == 2 and r[1] > 0:
                return float(r[0]) / float(r[1])
        return self.custom_locked_ratio

    def open_with_ratio(self, ratio_key: str):
        """Open the overlay pre-configured with a specific aspect ratio preset."""
        idx = self.combo_ratio.findData(ratio_key)
        if idx >= 0:
            self.combo_ratio.blockSignals(True)
            self.combo_ratio.setCurrentIndex(idx)
            self.combo_ratio.blockSignals(False)

        self._apply_preset_geometry(ratio_key)
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_ratio_combo_changed(self, index: int):
        ratio_key = self.combo_ratio.itemData(index) or "freeform"
        self._apply_preset_geometry(ratio_key)

    def _apply_preset_geometry(self, ratio_key: str):
        """Configure rectangle dimensions and lock state for the selected ratio."""
        self.current_ratio_key = ratio_key
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        sw = screen_geo.width()
        sh = screen_geo.height()

        self._populate_size_combo(ratio_key)

        if ratio_key == "freeform":
            self.is_ratio_locked = False
            self.custom_locked_ratio = None
            self.btn_lock.blockSignals(True)
            self.btn_lock.setChecked(False)
            self.btn_lock.setText("🔓 Free")
            self.btn_lock.blockSignals(False)
        else:
            self.is_ratio_locked = True
            self.custom_locked_ratio = None
            self.btn_lock.blockSignals(True)
            self.btn_lock.setChecked(True)
            self.btn_lock.setText("🔒 Locked")
            self.btn_lock.blockSignals(False)

            info = ASPECT_RATIO_PRESETS.get(ratio_key, {})
            def_size = info.get("default_size")
            ratio_tup = info.get("ratio")

            if def_size and ratio_tup:
                req_w, req_h = def_size
                # If fits nicely on screen with margin, use default size
                if req_w <= sw - 80 and req_h <= sh - 80:
                    w, h = req_w, req_h
                else:
                    # Scale down proportionally to 88% of screen height/width
                    ar = ratio_tup[0] / ratio_tup[1]
                    max_h = int((sh - 100) * 0.88)
                    max_w = int((sw - 100) * 0.88)

                    if max_h * ar <= max_w:
                        h = max_h
                        w = int(h * ar)
                    else:
                        w = max_w
                        h = int(w / ar)

                w = max(64, w - (w % 2))
                h = max(64, h - (h % 2))

                cx = self.selection_rect.center().x()
                cy = self.selection_rect.center().y()
                self.selection_rect = QRect(cx - w // 2, cy - h // 2, w, h)

        self._normalize_and_update()

    def _populate_size_combo(self, ratio_key: str):
        """Populate common resolutions for the chosen aspect ratio."""
        self.combo_size.blockSignals(True)
        self.combo_size.clear()

        info = ASPECT_RATIO_PRESETS.get(ratio_key, {})
        sizes = info.get("sizes", [])

        if sizes:
            for w, h in sizes:
                self.combo_size.addItem(f"{w} × {h}", (w, h))
            self.combo_size.addItem("Fit Screen", "fit")
            self.combo_size.setEnabled(True)
        else:
            self.combo_size.addItem("Custom Size", None)
            self.combo_size.addItem("Fit Screen", "fit")
            self.combo_size.setEnabled(True)

        self.combo_size.blockSignals(False)

    def _on_size_combo_changed(self, index: int):
        val = self.combo_size.itemData(index)
        if not val:
            return

        screen_geo = QApplication.primaryScreen().virtualGeometry()
        sw = screen_geo.width()
        sh = screen_geo.height()

        if val == "fit":
            ar = self.get_active_ratio()
            if ar:
                max_h = int((sh - 80) * 0.90)
                max_w = int((sw - 80) * 0.90)
                if max_h * ar <= max_w:
                    h = max_h
                    w = int(h * ar)
                else:
                    w = max_w
                    h = int(w / ar)
            else:
                w = int(sw * 0.75)
                h = int(sh * 0.75)
        else:
            w, h = val

        w = max(64, w - (w % 2))
        h = max(64, h - (h % 2))

        cx = self.selection_rect.center().x()
        cy = self.selection_rect.center().y()
        self.selection_rect = QRect(cx - w // 2, cy - h // 2, w, h)
        self._normalize_and_update()

    def _toggle_lock(self, checked: bool):
        self.is_ratio_locked = checked
        if checked:
            self.btn_lock.setText("🔒 Locked")
            if self.current_ratio_key == "freeform":
                norm = self.selection_rect.normalized()
                self.custom_locked_ratio = norm.width() / max(1, norm.height())
        else:
            self.btn_lock.setText("🔓 Free")
            self.custom_locked_ratio = None

    def _toggle_grid(self, checked: bool):
        self.show_grid = checked
        self.update()

    def _center_selection(self):
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.selection_rect.moveCenter(screen_geo.center())
        self._normalize_and_update()

    def _set_fullscreen(self):
        geo = QApplication.primaryScreen().virtualGeometry()
        self.selection_rect = QRect(0, 0, geo.width(), geo.height())
        self.current_ratio_key = "freeform"
        self.is_ratio_locked = False
        self.btn_lock.setChecked(False)
        self.combo_ratio.blockSignals(True)
        idx = self.combo_ratio.findData("freeform")
        if idx >= 0:
            self.combo_ratio.setCurrentIndex(idx)
        self.combo_ratio.blockSignals(False)
        self._normalize_and_update()

    def _update_hud_position(self):
        w = self.selection_rect.width()
        h = self.selection_rect.height()

        ratio_label = ""
        if self.current_ratio_key in ASPECT_RATIO_PRESETS and self.current_ratio_key != "freeform":
            ratio_label = f" ({ASPECT_RATIO_PRESETS[self.current_ratio_key]['label']})"

        self.lbl_dims.setText(f"{w} × {h}{ratio_label}")

        self.hud_frame.adjustSize()
        hud_w = self.hud_frame.width()
        hud_h = self.hud_frame.height()

        hud_x = self.selection_rect.center().x() - hud_w // 2
        hud_y = self.selection_rect.bottom() + 12

        if hud_y + hud_h > self.height() - 10:
            hud_y = self.selection_rect.top() - hud_h - 12

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
        # Even dimension enforcement for H.264
        w = norm.width() - (norm.width() % 2)
        h = norm.height() - (norm.height() % 2)
        w = max(64, w)
        h = max(64, h)

        preset_info = ASPECT_RATIO_PRESETS.get(self.current_ratio_key, {})
        ratio_name = preset_info.get("name", "Custom Region")
        ratio_label = preset_info.get("label", "Custom")

        region = {
            "left": norm.left(),
            "top": norm.top(),
            "width": w,
            "height": h,
            "ratio_key": self.current_ratio_key,
            "ratio_name": ratio_name,
            "ratio_label": ratio_label,
        }
        self.hide()
        self.region_selected.emit(region)

    def _cancel(self):
        self.hide()
        self.cancelled.emit()

    def keyPressEvent(self, event):
        step = 10 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 2
        r = QRect(self.selection_rect)

        if event.key() == Qt.Key.Key_Left:
            r.translate(-step, 0)
            self.selection_rect = r
            self._normalize_and_update()
            return
        elif event.key() == Qt.Key.Key_Right:
            r.translate(step, 0)
            self.selection_rect = r
            self._normalize_and_update()
            return
        elif event.key() == Qt.Key.Key_Up:
            r.translate(0, -step)
            self.selection_rect = r
            self._normalize_and_update()
            return
        elif event.key() == Qt.Key.Key_Down:
            r.translate(0, step)
            self.selection_rect = r
            self._normalize_and_update()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel()
            return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._confirm()
            return
        super().keyPressEvent(event)

    def _get_handle_at(self, pos: QPoint) -> int:
        r = self.selection_rect.normalized()
        hs = self.HANDLE_SIZE + 4  # Generous hit target (14px)

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

        # Inside the selection rectangle OR slightly on the border (6px margin)
        if r.adjusted(-6, -6, 6, 6).contains(pos):
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
        ratio = self.get_active_ratio()

        if self.is_selecting:
            dx = pos.x() - self.drag_start_pos.x()
            dy = pos.y() - self.drag_start_pos.y()
            sign_x = 1 if dx >= 0 else -1
            sign_y = 1 if dy >= 0 else -1
            raw_w = max(1, abs(dx))
            raw_h = max(1, abs(dy))

            if ratio:
                if raw_w / ratio > raw_h:
                    w = raw_w
                    h = int(w / ratio)
                else:
                    h = raw_h
                    w = int(h * ratio)
            else:
                w, h = raw_w, raw_h

            w = max(64, w - (w % 2))
            h = max(64, h - (h % 2))

            sx = self.drag_start_pos.x()
            sy = self.drag_start_pos.y()
            left = sx if sign_x > 0 else sx - w
            top = sy if sign_y > 0 else sy - h
            self.selection_rect = QRect(left, top, w, h)
            self._normalize_and_update()

        elif self.is_resizing:
            diff = pos - self.drag_start_pos
            init = self.initial_rect

            if self.current_handle == self.HANDLE_MOVE:
                r = QRect(init)
                r.translate(diff)
                self.selection_rect = r
                self._normalize_and_update()
                return

            if ratio:
                # --- LOCKED ASPECT RATIO RESIZING ---
                if self.current_handle == self.HANDLE_BR:
                    x0, y0 = init.left(), init.top()
                    raw_w = max(1, pos.x() - x0)
                    raw_h = max(1, pos.y() - y0)
                    if raw_w / ratio > raw_h:
                        w = raw_w
                        h = int(w / ratio)
                    else:
                        h = raw_h
                        w = int(h * ratio)
                    w = max(64, w - (w % 2))
                    h = max(64, h - (h % 2))
                    self.selection_rect = QRect(x0, y0, w, h)

                elif self.current_handle == self.HANDLE_BL:
                    x1, y0 = init.right(), init.top()
                    raw_w = max(1, x1 - pos.x())
                    raw_h = max(1, pos.y() - y0)
                    if raw_w / ratio > raw_h:
                        w = raw_w
                        h = int(w / ratio)
                    else:
                        h = raw_h
                        w = int(h * ratio)
                    w = max(64, w - (w % 2))
                    h = max(64, h - (h % 2))
                    self.selection_rect = QRect(x1 - w, y0, w, h)

                elif self.current_handle == self.HANDLE_TR:
                    x0, y1 = init.left(), init.bottom()
                    raw_w = max(1, pos.x() - x0)
                    raw_h = max(1, y1 - pos.y())
                    if raw_w / ratio > raw_h:
                        w = raw_w
                        h = int(w / ratio)
                    else:
                        h = raw_h
                        w = int(h * ratio)
                    w = max(64, w - (w % 2))
                    h = max(64, h - (h % 2))
                    self.selection_rect = QRect(x0, y1 - h, w, h)

                elif self.current_handle == self.HANDLE_TL:
                    x1, y1 = init.right(), init.bottom()
                    raw_w = max(1, x1 - pos.x())
                    raw_h = max(1, y1 - pos.y())
                    if raw_w / ratio > raw_h:
                        w = raw_w
                        h = int(w / ratio)
                    else:
                        h = raw_h
                        w = int(h * ratio)
                    w = max(64, w - (w % 2))
                    h = max(64, h - (h % 2))
                    self.selection_rect = QRect(x1 - w, y1 - h, w, h)

                elif self.current_handle == self.HANDLE_R:
                    x0 = init.left()
                    cy = init.center().y()
                    raw_w = max(64, pos.x() - x0)
                    h = int(raw_w / ratio)
                    w = max(64, raw_w - (raw_w % 2))
                    h = max(64, h - (h % 2))
                    self.selection_rect = QRect(x0, cy - h // 2, w, h)

                elif self.current_handle == self.HANDLE_L:
                    x1 = init.right()
                    cy = init.center().y()
                    raw_w = max(64, x1 - pos.x())
                    h = int(raw_w / ratio)
                    w = max(64, raw_w - (raw_w % 2))
                    h = max(64, h - (h % 2))
                    self.selection_rect = QRect(x1 - w, cy - h // 2, w, h)

                elif self.current_handle == self.HANDLE_B:
                    y0 = init.top()
                    cx = init.center().x()
                    raw_h = max(64, pos.y() - y0)
                    w = int(raw_h * ratio)
                    w = max(64, w - (w % 2))
                    h = max(64, raw_h - (raw_h % 2))
                    self.selection_rect = QRect(cx - w // 2, y0, w, h)

                elif self.current_handle == self.HANDLE_T:
                    y1 = init.bottom()
                    cx = init.center().x()
                    raw_h = max(64, y1 - pos.y())
                    w = int(raw_h * ratio)
                    w = max(64, w - (w % 2))
                    h = max(64, raw_h - (raw_h % 2))
                    self.selection_rect = QRect(cx - w // 2, y1 - h, w, h)

            else:
                # --- UNCONSTRAINED (FREEFORM) RESIZING ---
                r = QRect(init)
                if self.current_handle == self.HANDLE_TL:
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
            # Update hover cursor
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

        # Cutout transparent selected area
        r = self.selection_rect.normalized()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(r, Qt.GlobalColor.transparent)

        # Crucial for Windows layered window hit-testing:
        # Paint near-zero alpha (alpha = 1) over the cutout area.
        # This makes it 100% crystal-clear to the user, but ensures Windows Desktop Window Manager
        # intercepts mouse clicks, moves, and drags inside the box instead of passing through to underlying apps!
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.fillRect(r, QColor(0, 0, 0, 1))

        # Draw glowing bounding border around selection
        border_pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)
        painter.drawRect(r)

        # Draw Rule of Thirds framing guides
        if self.show_grid and r.width() > 100 and r.height() > 100:
            grid_pen = QPen(QColor(255, 255, 255, 65), 1, Qt.PenStyle.DashLine)
            painter.setPen(grid_pen)
            # 2 vertical lines
            x1 = r.left() + r.width() // 3
            x2 = r.left() + (2 * r.width()) // 3
            painter.drawLine(x1, r.top(), x1, r.bottom())
            painter.drawLine(x2, r.top(), x2, r.bottom())
            # 2 horizontal lines
            y1 = r.top() + r.height() // 3
            y2 = r.top() + (2 * r.height()) // 3
            painter.drawLine(r.left(), y1, r.right(), y1)
            painter.drawLine(r.left(), y2, r.right(), y2)

        # Center Move Helper Badge
        if r.width() >= 140 and r.height() >= 60:
            badge_text = "✥ Drag anywhere to move"
            badge_font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
            painter.setFont(badge_font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(badge_text) + 16
            th = fm.height() + 6
            badge_rect = QRect(r.center().x() - tw // 2, r.center().y() - th // 2, tw, th)

            painter.setBrush(QBrush(QColor(19, 21, 29, 160)))
            painter.setPen(QPen(QColor(COLOR_ACCENT), 1))
            painter.drawRoundedRect(badge_rect, 5, 5)

            painter.setPen(QPen(QColor("#E0E7FF")))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

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

