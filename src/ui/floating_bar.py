"""
Floating minimal recording toolbar widget.
"""

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QApplication,
    QMenu,
)
from src.config.constants import WEBCAM_SHAPES, WEBCAM_FILTERS


class FloatingBar(QWidget):
    """Sleek floating capsule control bar shown during recording."""

    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    annotate_clicked = pyqtSignal()
    screenshot_clicked = pyqtSignal()
    toggle_webcam_clicked = pyqtSignal()
    toggle_webcam_fullscreen_clicked = pyqtSignal()
    webcam_size_changed = pyqtSignal(int)
    webcam_shape_changed = pyqtSignal(str)
    webcam_filter_changed = pyqtSignal(str)
    restore_main_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.drag_start = QPoint()
        self.is_dragging = False
        self.is_paused = False
        self.is_cam_fullscreen = False

        self._setup_ui()

        # Position at top-center of screen by default
        screen_geo = QApplication.primaryScreen().geometry()
        self.move((screen_geo.width() - self.width()) // 2, 24)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Capsule Container Frame
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(22, 24, 32, 0.95);
                border: 1px solid #3F4458;
                border-radius: 22px;
            }
            QLabel {
                color: #F9FAFB;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }
            QPushButton {
                background-color: #20232E;
                color: #F3F4F6;
                border: 1px solid #2D313F;
                border-radius: 14px;
                padding: 6px 11px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2B2F3D;
                border-color: #6366F1;
            }
            QPushButton#BtnStop {
                background-color: #EF4444;
                border-color: #DC2626;
                color: white;
            }
            QPushButton#BtnStop:hover {
                background-color: #DC2626;
            }
            QPushButton#BtnCamModeActive {
                background-color: #4F46E5;
                border-color: #818CF8;
                color: white;
            }
            QPushButton#BtnCamModeActive:hover {
                background-color: #4338CA;
            }
        """)

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Drag Grip icon
        self.lbl_grip = QLabel("⠿", self.frame)
        self.lbl_grip.setStyleSheet("color: #6B7280; font-size: 16px;")
        layout.addWidget(self.lbl_grip)

        # Pulsing Red Dot & Timer
        self.lbl_dot = QLabel("🔴", self.frame)
        layout.addWidget(self.lbl_dot)

        self.lbl_timer = QLabel("00:00", self.frame)
        self.lbl_timer.setFixedWidth(48)
        layout.addWidget(self.lbl_timer)

        self.lbl_fps = QLabel("60 FPS", self.frame)
        self.lbl_fps.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: normal;")
        layout.addWidget(self.lbl_fps)

        # Separator line
        sep = QFrame(self.frame)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #2D313F; max-width: 1px;")
        layout.addWidget(sep)

        # Control Buttons
        self.btn_pause = QPushButton("⏸ Pause", self.frame)
        self.btn_pause.setToolTip("Pause / Resume Recording (F10)")
        self.btn_pause.clicked.connect(self._toggle_pause)
        layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Stop", self.frame)
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setToolTip("Stop & Save Recording (F9)")
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.btn_stop)

        self.btn_draw = QPushButton("✏️ Draw", self.frame)
        self.btn_draw.setToolTip("Toggle Annotations Canvas (F8)")
        self.btn_draw.clicked.connect(self.annotate_clicked.emit)
        layout.addWidget(self.btn_draw)

        # Webcam Toggle button
        self.btn_cam = QPushButton("📷", self.frame)
        self.btn_cam.setToolTip("Toggle Webcam PiP (F7) • Right-click for Size & Preset Menu")
        self.btn_cam.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_cam.customContextMenuRequested.connect(lambda pos: self._show_cam_size_menu())
        self.btn_cam.clicked.connect(self.toggle_webcam_clicked.emit)
        layout.addWidget(self.btn_cam)

        # 1-Click Fullscreen / Presenter Cam mode button
        self.btn_cam_mode = QPushButton("⛶ Full", self.frame)
        self.btn_cam_mode.setToolTip("Toggle Fullscreen Presenter Cam Mode (F4)\nCovers entire recording area with webcam")
        self.btn_cam_mode.clicked.connect(self.toggle_webcam_fullscreen_clicked.emit)
        layout.addWidget(self.btn_cam_mode)

        # Quick size & options menu button
        self.btn_cam_size = QPushButton("📐 Size ▾", self.frame)
        self.btn_cam_size.setToolTip("Quick Webcam Sizing, Framing Shapes & Studio Filters")
        self.btn_cam_size.clicked.connect(self._show_cam_size_menu)
        layout.addWidget(self.btn_cam_size)

        self.btn_screenshot = QPushButton("📸", self.frame)
        self.btn_screenshot.setToolTip("Take HD Screenshot (F11)")
        self.btn_screenshot.clicked.connect(self.screenshot_clicked.emit)
        layout.addWidget(self.btn_screenshot)

        self.btn_expand = QPushButton("🗖", self.frame)
        self.btn_expand.setToolTip("Show Main Dashboard")
        self.btn_expand.clicked.connect(self.restore_main_clicked.emit)
        layout.addWidget(self.btn_expand)

        main_layout.addWidget(self.frame)
        self.adjustSize()

    def update_time(self, elapsed_seconds: int):
        mins = elapsed_seconds // 60
        secs = elapsed_seconds % 60
        self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")

    def update_fps(self, fps: float):
        self.lbl_fps.setText(f"{fps:.0f} FPS")

    def _toggle_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.setText("⏸ Pause")
            self.lbl_dot.setText("🔴")
            self.resume_clicked.emit()
        else:
            self.is_paused = True
            self.btn_pause.setText("▶ Resume")
            self.lbl_dot.setText("⏸️")
            self.pause_clicked.emit()

    def set_paused_state(self, is_paused: bool):
        self.is_paused = is_paused
        if is_paused:
            self.btn_pause.setText("▶ Resume")
            self.lbl_dot.setText("⏸️")
        else:
            self.btn_pause.setText("⏸ Pause")
            self.lbl_dot.setText("🔴")

    def update_webcam_mode(self, is_fullscreen: bool):
        """Update webcam mode button state and styling."""
        self.is_cam_fullscreen = is_fullscreen
        if is_fullscreen:
            self.btn_cam_mode.setText("🗗 PiP")
            self.btn_cam_mode.setObjectName("BtnCamModeActive")
            self.btn_cam_mode.setToolTip("Restore Floating PiP Mode (F4 or Esc)")
        else:
            self.btn_cam_mode.setText("⛶ Full")
            self.btn_cam_mode.setObjectName("")
            self.btn_cam_mode.setToolTip("Expand Webcam to Cover Whole Recording Area (F4)")

        # Re-apply stylesheet to update button style
        self.frame.style().unpolish(self.btn_cam_mode)
        self.frame.style().polish(self.btn_cam_mode)

    def _show_cam_size_menu(self):
        """Show sleek popup menu for webcam sizing, mode toggle, framing shapes, and filters."""
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
                padding: 6px 20px;
                border-radius: 4px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #6366F1;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2D313F;
                margin: 4px 6px;
            }
        """)

        # 1. Fullscreen Presenter Toggle
        if self.is_cam_fullscreen:
            act_mode = menu.addAction("🗗 Restore Floating PiP Mode (Esc)")
        else:
            act_mode = menu.addAction("⛶ Full Presenter Cam (Cover Recording Area)")
        act_mode.triggered.connect(self.toggle_webcam_fullscreen_clicked.emit)

        menu.addSeparator()

        # 2. PiP Size Presets
        menu_sizes = menu.addMenu("📏 Webcam Size Presets")
        for sz, lbl in [
            (140, "Compact (140px)"),
            (220, "Medium (220px)"),
            (320, "Large (320px)"),
            (420, "Extra Large (420px)"),
            (520, "Jumbo (520px)"),
        ]:
            act = menu_sizes.addAction(lbl)
            act.triggered.connect(lambda checked, s=sz: self.webcam_size_changed.emit(s))

        # 3. Framing Shapes
        menu_shapes = menu.addMenu("🔲 Framing & Shape")
        for s_key, s_info in WEBCAM_SHAPES.items():
            act = menu_shapes.addAction(f"{s_info['icon']} {s_info['name']}")
            act.triggered.connect(lambda checked, k=s_key: self.webcam_shape_changed.emit(k))

        # 4. Studio Lighting & Filters
        menu_filters = menu.addMenu("☀️ Studio Lighting & Filters")
        for f_key, f_info in WEBCAM_FILTERS.items():
            act = menu_filters.addAction(f"{f_info['icon']} {f_info['name']}")
            act.triggered.connect(lambda checked, k=f_key: self.webcam_filter_changed.emit(k))

        menu.addSeparator()

        # 5. Toggle Cam On/Off
        act_toggle = menu.addAction("📷 Toggle Webcam PiP (F7)")
        act_toggle.triggered.connect(self.toggle_webcam_clicked.emit)

        # Position menu beneath btn_cam_size or near cursor
        btn_pos = self.btn_cam_size.mapToGlobal(QPoint(0, self.btn_cam_size.height() + 4))
        menu.exec(btn_pos)

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
