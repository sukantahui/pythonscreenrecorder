"""
System tray icon and native desktop notifications service.
"""

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from src.config.constants import APP_NAME, COLOR_ACCENT, COLOR_DANGER


class TrayService(QObject):
    """Manages system tray presence and quick actions."""

    show_requested = pyqtSignal()
    record_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    manual_requested = pyqtSignal()
    about_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self.icon_idle = self._generate_icon(COLOR_ACCENT)
        self.icon_recording = self._generate_icon(COLOR_DANGER)

        self.tray_icon.setIcon(self.icon_idle)
        self.tray_icon.setToolTip(APP_NAME)
        self._setup_menu()

        self.tray_icon.activated.connect(self._on_tray_activated)

    def _generate_icon(self, color_hex: str) -> QIcon:
        """Draw a vector badge icon in memory."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer rounded square
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 8, 8)

        # Inner white camera lens circle
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(10, 10, 12, 12)
        painter.end()

        return QIcon(pixmap)

    def _setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #161820;
                color: #F9FAFB;
                border: 1px solid #2D313F;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #6366F1;
            }
        """)

        action_show = menu.addAction("Show Recorder")
        action_show.triggered.connect(self.show_requested.emit)

        menu.addSeparator()

        self.action_record = menu.addAction("Start Recording")
        self.action_record.triggered.connect(self.record_requested.emit)

        self.action_pause = menu.addAction("Pause Recording")
        self.action_pause.setEnabled(False)
        self.action_pause.triggered.connect(self.pause_requested.emit)

        self.action_stop = menu.addAction("Stop Recording")
        self.action_stop.setEnabled(False)
        self.action_stop.triggered.connect(self.stop_requested.emit)

        menu.addSeparator()

        action_folder = menu.addAction("Open Output Folder")
        action_folder.triggered.connect(self.open_folder_requested.emit)

        action_settings = menu.addAction("Settings")
        action_settings.triggered.connect(self.settings_requested.emit)

        action_manual = menu.addAction("📖 User Manual & Docs...")
        action_manual.triggered.connect(self.manual_requested.emit)

        action_about = menu.addAction("About Coder & AccoTax (CNAT)...")
        action_about.triggered.connect(self.about_requested.emit)

        menu.addSeparator()

        action_exit = menu.addAction("Exit")
        action_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)

    def show(self):
        self.tray_icon.show()

    def set_recording_state(self, is_recording: bool, is_paused: bool = False):
        if is_recording:
            self.tray_icon.setIcon(self.icon_recording)
            self.tray_icon.setToolTip(f"{APP_NAME} - Recording...")
            self.action_record.setEnabled(False)
            self.action_pause.setEnabled(True)
            self.action_pause.setText("Resume Recording" if is_paused else "Pause Recording")
            self.action_stop.setEnabled(True)
        else:
            self.tray_icon.setIcon(self.icon_idle)
            self.tray_icon.setToolTip(APP_NAME)
            self.action_record.setEnabled(True)
            self.action_pause.setEnabled(False)
            self.action_stop.setEnabled(False)

    def show_notification(self, title: str, message: str):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()
