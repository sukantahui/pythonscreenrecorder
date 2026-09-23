"""
Unit tests for PreviewDialog audio/video playback and controls.
"""

import os
import unittest
from PyQt6.QtWidgets import QApplication
from src.ui.preview_dialog import PreviewDialog


class TestPreviewDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_dialog_initialization(self):
        video_path = r"tests\test_output\Record_2026-09-23_23-01-48.mp4"
        if not os.path.exists(video_path):
            self.skipTest("Sample recording not present")

        dlg = PreviewDialog(video_path)
        self.assertIsNotNone(dlg.player)
        self.assertIsNotNone(dlg.audio_output)
        self.assertIsNotNone(dlg.video_widget)

        # Volume & Mute checks
        dlg._on_volume_changed(75)
        self.assertAlmostEqual(dlg.audio_output.volume(), 0.75, places=1)

        dlg._toggle_mute()
        self.assertTrue(dlg.audio_output.isMuted())

        dlg._toggle_mute()
        self.assertFalse(dlg.audio_output.isMuted())

        dlg.close()


if __name__ == "__main__":
    unittest.main()
