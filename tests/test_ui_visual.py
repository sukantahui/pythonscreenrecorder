"""
Visual verification script for Webcam Fullscreen Presenter Mode and Floating Bar.
"""

import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QRect
from src.ui.main_window import MainWindow
from src.ui.floating_bar import FloatingBar

def capture_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    with open("src/ui/styles.qss", "r") as f:
        app.setStyleSheet(f.read())

    # 1. Test MainWindow
    win = MainWindow()
    win.show()
    app.processEvents()

    win_pix = win.grab()
    os.makedirs("tests/test_output", exist_ok=True)
    win_pix.save("tests/test_output/main_window_presenter_ui.png")
    print("[UI Test] Saved main window screenshot.")

    # 2. Test FloatingBar
    bar = FloatingBar()
    bar.show()
    app.processEvents()

    bar_pix = bar.grab()
    bar_pix.save("tests/test_output/floating_bar_presenter_ui.png")
    print("[UI Test] Saved floating bar screenshot.")

    # 3. Test FloatingBar Active Fullscreen Cam state
    bar.update_webcam_mode(True)
    app.processEvents()
    bar_pix2 = bar.grab()
    bar_pix2.save("tests/test_output/floating_bar_presenter_active_ui.png")
    print("[UI Test] Saved floating bar active fullscreen cam screenshot.")

    # 4. Test WebcamPiPOverlay Circle Hover
    from src.overlays.webcam_pip import WebcamPiPOverlay
    overlay = WebcamPiPOverlay(shape="circle", size=220)
    overlay._is_hovered = True
    overlay.show()
    app.processEvents()

    cam_pix = overlay.grab()
    cam_pix.save("tests/test_output/webcam_pip_circle_hover_ui.png")
    print("[UI Test] Saved webcam circle hover screenshot.")

    # 5. Test UserManualDialog
    from src.ui.manual_dialog import UserManualDialog
    manual_dlg = UserManualDialog()
    manual_dlg.show()
    app.processEvents()

    manual_pix = manual_dlg.grab()
    manual_pix.save("tests/test_output/manual_dialog_ui.png")
    print("[UI Test] Saved user manual dialog screenshot.")

    win.close()
    bar.close()
    overlay.close()
    manual_dlg.close()

if __name__ == "__main__":
    capture_ui()
