"""
Apex Screen Recorder - Main Application Entrypoint.
"""

import sys
import os
import ctypes
from pathlib import Path

# Set Windows AppUserModelID for proper taskbar grouping & icon display
try:
    myappid = "codernaccotax.cnatscreenrecorder.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# Add project root / PyInstaller MEIPASS to sys.path
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))

# Windows High-DPI handling is managed natively by Qt6 (Per-Monitor Aware V2)

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
import signal
from src.config.constants import APP_NAME, APP_VERSION
from src.ui.main_window import MainWindow


def load_stylesheet(app: QApplication):
    """Load the master dark glassmorphic QSS stylesheet."""
    qss_path = PROJECT_ROOT / "src" / "ui" / "styles.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def load_icon(app: QApplication):
    """Set application window and taskbar icon."""
    for icon_name in ("app_icon.ico", "app_icon.png"):
        icon_path = PROJECT_ROOT / "assets" / icon_name
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Coder & AccoTax")
    app.setOrganizationDomain("codernaccotax.co.in")

    # Graceful terminal Ctrl+C exit handler
    signal.signal(signal.SIGINT, lambda *args: app.quit())
    sig_timer = QTimer()
    sig_timer.start(500)
    sig_timer.timeout.connect(lambda: None)

    # Load styling & icon
    load_stylesheet(app)
    load_icon(app)

    # Launch Main Window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
