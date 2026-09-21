"""
Apex Screen Recorder - Main Application Entrypoint.
"""

import sys
import os
import ctypes
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows High-DPI handling is managed natively by Qt6
# os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from src.config.constants import APP_NAME, APP_VERSION
from src.ui.main_window import MainWindow


def load_stylesheet(app: QApplication):
    """Load the master dark glassmorphic QSS stylesheet."""
    qss_path = PROJECT_ROOT / "src" / "ui" / "styles.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Antigravity")

    # Load styling
    load_stylesheet(app)

    # Launch Main Window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
