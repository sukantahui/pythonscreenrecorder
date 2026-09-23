"""
Floating minimal recording toolbar widget.
"""

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QApplication,
)


class FloatingBar(QWidget):
    """Sleek floating capsule control bar shown during recording."""

    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    annotate_clicked = pyqtSignal()
    screenshot_clicked = pyqtSignal()
    toggle_webcam_clicked = pyqtSignal()
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
                padding: 6px 12px;
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
        """)

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # Drag Grip icon
        self.lbl_grip = QLabel("⠿", self.frame)
        self.lbl_grip.setStyleSheet("color: #6B7280; font-size: 16px;")
        layout.addWidget(self.lbl_grip)

        # Pulsing Red Dot & Timer
        self.lbl_dot = QLabel("🔴", self.frame)
        layout.addWidget(self.lbl_dot)

        self.lbl_timer = QLabel("00:00", self.frame)
        self.lbl_timer.setFixedWidth(52)
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
        self.btn_pause.clicked.connect(self._toggle_pause)
        layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Stop", self.frame)
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.btn_stop)

        self.btn_draw = QPushButton("✏️ Draw", self.frame)
        self.btn_draw.clicked.connect(self.annotate_clicked.emit)
        layout.addWidget(self.btn_draw)

        self.btn_cam = QPushButton("📷", self.frame)
        self.btn_cam.setToolTip("Toggle Webcam PiP")
        self.btn_cam.clicked.connect(self.toggle_webcam_clicked.emit)
        layout.addWidget(self.btn_cam)

        self.btn_screenshot = QPushButton("📸", self.frame)
        self.btn_screenshot.setToolTip("Take Screenshot (F11)")
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
