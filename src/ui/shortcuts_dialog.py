"""
Keyboard shortcuts reference dialog for CNAT Screen Recorder.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
)
from src.config.constants import APP_NAME, COMPANY_NAME, COMPANY_SHORT


class ShortcutsDialog(QDialog):
    """Modern cheatsheet dialog showing all keyboard shortcuts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Keyboard Shortcuts")
        self.setFixedSize(520, 480)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        lbl_title = QLabel("⌨️ Keyboard Shortcuts & Controls")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Master quick actions with high-speed hotkeys during recordings.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        layout.addWidget(lbl_sub)

        # Shortcuts Table Card
        card = QFrame(self)
        card.setProperty("class", "Card")
        grid = QGridLayout(card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(12)

        shortcuts = [
            ("F9", "Start / Stop Screen Recording", "#EF4444"),
            ("F10", "Pause / Resume Recording", "#F59E0B"),
            ("F8", "Toggle Drawing & Annotations Canvas", "#6366F1"),
            ("F7", "Toggle Webcam PiP (Picture-in-Picture)", "#818CF8"),
            ("F6", "Mute / Unmute Microphone", "#10B981"),
            ("F11", "Take Instant HD Screenshot", "#3B82F6"),
            ("Mouse Wheel", "Resize Webcam PiP dynamically", "#EC4899"),
            ("Right Click Cam", "Open Webcam Shape, Size & Mirror Menu", "#A855F7"),
            ("Esc", "Exit Region Selection / Clear Annotations", "#6B7280"),
        ]

        for row, (key_combo, description, color) in enumerate(shortcuts):
            # Key badge
            badge = QLabel(f" {key_combo} ")
            badge.setStyleSheet(f"""
                background-color: #20232E;
                color: #F9FAFB;
                border: 1px solid #3F4458;
                border-bottom: 2px solid {color};
                border-radius: 6px;
                padding: 4px 8px;
                font-family: monospace;
                font-size: 12px;
                font-weight: bold;
            """)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(badge, row, 0)

            # Description
            desc = QLabel(description)
            desc.setStyleSheet("font-size: 13px; color: #E5E7EB;")
            grid.addWidget(desc, row, 1)

        layout.addWidget(card)
        layout.addStretch()

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Got it")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
