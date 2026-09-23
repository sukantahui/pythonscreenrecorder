"""
Unit tests for Fullscreen Presenter Cam Mode, dynamic resizing mid-recording,
and toolbar integration.
"""

import sys
import unittest
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtWidgets import QApplication

# Ensure single QApplication instance
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.overlays.webcam_pip import WebcamPiPOverlay
from src.ui.floating_bar import FloatingBar
from src.config.constants import WEBCAM_SHAPES, WEBCAM_FILTERS, HOTKEY_WEBCAM_FULLSCREEN
from src.services.hotkey_service import hotkey_service


class TestWebcamPresenterFullscreen(unittest.TestCase):
    """Test suite for Presenter Fullscreen Cam and dynamic mid-recording sizing."""

    def setUp(self):
        self.overlay = WebcamPiPOverlay(
            device_id=0,
            shape="wide",
            size=220,
            mirrored=True,
            filter_name="normal",
            border_theme="indigo",
        )

    def tearDown(self):
        if self.overlay:
            self.overlay.stop()
            self.overlay.deleteLater()

    def test_initial_pip_dimensions(self):
        """Verify standard 16:9 PiP aspect ratio calculation."""
        w, h = self.overlay._get_pip_dimensions()
        self.assertEqual(h, 220)
        self.assertEqual(w, int(220 * 16 / 9))
        self.assertFalse(self.overlay.is_fullscreen_cam)

    def test_toggle_fullscreen_cam_screen(self):
        """Test toggling to fullscreen presenter mode on primary display."""
        screen = QApplication.primaryScreen()
        screen_geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)

        # 1. Expand to Fullscreen Cam
        mode_signals = []
        self.overlay.mode_changed.connect(mode_signals.append)

        self.overlay.toggle_fullscreen_cam()
        self.assertTrue(self.overlay.is_fullscreen_cam)
        self.assertEqual(len(mode_signals), 1)
        self.assertTrue(mode_signals[0])
        self.assertEqual(self.overlay.width(), screen_geo.width())
        self.assertEqual(self.overlay.height(), screen_geo.height())

        # 2. Restore to PiP
        self.overlay.toggle_fullscreen_cam()
        self.assertFalse(self.overlay.is_fullscreen_cam)
        self.assertEqual(len(mode_signals), 2)
        self.assertFalse(mode_signals[1])
        w, h = self.overlay._get_pip_dimensions()
        self.assertEqual(self.overlay.width(), w)
        self.assertEqual(self.overlay.height(), h)

    def test_toggle_fullscreen_cam_custom_region(self):
        """Test covering a specific recording region exactly with webcam."""
        custom_region = {"left": 100, "top": 150, "width": 800, "height": 600}
        self.overlay.set_recording_region(custom_region)

        # Expand to cover region
        self.overlay.toggle_fullscreen_cam()
        self.assertTrue(self.overlay.is_fullscreen_cam)
        self.assertEqual(self.overlay.width(), 800)
        self.assertEqual(self.overlay.height(), 600)
        self.assertEqual(self.overlay.x(), 100)
        self.assertEqual(self.overlay.y(), 150)

        # Restore back to PiP
        self.overlay.toggle_fullscreen_cam()
        self.assertFalse(self.overlay.is_fullscreen_cam)
        w, h = self.overlay._get_pip_dimensions()
        self.assertEqual(self.overlay.width(), w)
        self.assertEqual(self.overlay.height(), h)

    def test_dynamic_size_presets(self):
        """Test seamless dynamic resizing across presets."""
        sizes_to_test = [140, 220, 320, 420, 520]
        for sz in sizes_to_test:
            self.overlay.set_size(sz)
            self.assertEqual(self.overlay.pip_size, sz)
            w, h = self.overlay._get_pip_dimensions()
            self.assertEqual(h, sz)
            self.assertEqual(w, int(sz * 16 / 9))

    def test_shape_and_filter_cycling(self):
        """Test cycling shapes and studio filters."""
        self.overlay.set_shape("circle")
        self.assertEqual(self.overlay.shape_type, "circle")
        w, h = self.overlay._get_pip_dimensions()
        self.assertEqual(w, h)

        self.overlay.set_filter("warm")
        self.assertEqual(self.overlay.filter_type, "warm")

        self.overlay.set_border_theme("cyan")
        self.assertEqual(self.overlay.border_theme, "cyan")


class TestFloatingBarIntegration(unittest.TestCase):
    """Test suite for floating control toolbar actions and presenter buttons."""

    def setUp(self):
        self.bar = FloatingBar()

    def tearDown(self):
        if self.bar:
            self.bar.close()
            self.bar.deleteLater()

    def test_floating_bar_presenter_signals(self):
        """Verify signals emitted from FloatingBar buttons."""
        fs_signals = []
        size_signals = []
        shape_signals = []
        filter_signals = []

        self.bar.toggle_webcam_fullscreen_clicked.connect(lambda: fs_signals.append(True))
        self.bar.webcam_size_changed.connect(size_signals.append)
        self.bar.webcam_shape_changed.connect(shape_signals.append)
        self.bar.webcam_filter_changed.connect(filter_signals.append)

        # Trigger presenter button
        self.bar.btn_cam_mode.click()
        self.assertEqual(len(fs_signals), 1)

        # Trigger size preset signal
        self.bar.webcam_size_changed.emit(320)
        self.assertEqual(size_signals, [320])

        # Trigger shape and filter signals
        self.bar.webcam_shape_changed.emit("circle")
        self.assertEqual(shape_signals, ["circle"])
        self.bar.webcam_filter_changed.emit("beauty")
        self.assertEqual(filter_signals, ["beauty"])

    def test_update_webcam_mode_ui(self):
        """Test FloatingBar button state when webcam switches between PiP and Fullscreen."""
        self.bar.update_webcam_mode(True)
        self.assertEqual(self.bar.btn_cam_mode.text(), "🗗 PiP")
        self.assertTrue(self.bar.is_cam_fullscreen)

        self.bar.update_webcam_mode(False)
        self.assertEqual(self.bar.btn_cam_mode.text(), "⛶ Full")
        self.assertFalse(self.bar.is_cam_fullscreen)

    def test_hotkey_constant(self):
        """Verify F4 hotkey constant is configured."""
        self.assertEqual(HOTKEY_WEBCAM_FULLSCREEN, "F4")


if __name__ == "__main__":
    unittest.main()
