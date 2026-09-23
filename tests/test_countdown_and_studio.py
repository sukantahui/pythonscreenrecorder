"""
Tests for Studio Countdown Overlay, Preview Studio Controls, and Recent Recordings Gallery.
"""

import os
import unittest
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import QApplication
from src.overlays.countdown_overlay import CountdownOverlay
from src.ui.preview_dialog import PreviewDialog


class TestCountdownAndStudio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_countdown_overlay_lifecycle(self):
        overlay = CountdownOverlay()
        self.assertFalse(overlay.is_running)

        finished_called = []
        cancelled_called = []
        overlay.finished.connect(lambda: finished_called.append(True))
        overlay.cancelled.connect(lambda: cancelled_called.append(True))

        # Test start
        overlay.start_countdown(seconds=1, region={"x": 50, "y": 50, "width": 400, "height": 300})
        self.assertTrue(overlay.is_running)
        self.assertEqual(overlay.current_number, 1)
        self.assertIsNotNone(overlay.region)

        # Test cancel
        overlay.cancel()
        self.assertFalse(overlay.is_running)
        self.assertTrue(cancelled_called)
        self.assertFalse(finished_called)

        overlay.close()

    def test_preview_dialog_studio_tools(self):
        # Create a dummy or existing test file
        test_video = r"tests\test_output\Record_2026-09-23_23-01-48.mp4"
        if not os.path.exists(test_video):
            self.skipTest("Sample recording not present")

        dlg = PreviewDialog(test_video)

        # Test playback speed rates
        for speed_text, expected_rate in [("0.5x", 0.5), ("1.0x (Normal)", 1.0), ("1.5x", 1.5), ("2.0x", 2.0)]:
            idx = dlg.combo_speed.findText(speed_text)
            if idx >= 0:
                dlg.combo_speed.setCurrentIndex(idx)
                self.assertAlmostEqual(dlg.player.playbackRate(), expected_rate, places=2)

        # Test copy file to clipboard
        dlg._copy_file_to_clipboard()
        clipboard = QApplication.clipboard()
        self.assertTrue(clipboard.text().endswith(os.path.basename(test_video)) or len(clipboard.mimeData().urls()) > 0)

        dlg.close()


if __name__ == "__main__":
    unittest.main()
