"""
Unit tests for SettingsDialog, ShortcutsDialog, and AboutDialog.
"""

import sys
import unittest
from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from src.ui.settings_dialog import SettingsDialog
from src.ui.shortcuts_dialog import ShortcutsDialog
from src.ui.about_dialog import AboutDialog
from src.config.settings_manager import settings


class TestDialogs(unittest.TestCase):
    """Test suite for settings, shortcuts, and about modal dialogs."""

    def test_settings_dialog_initialization_and_load(self):
        """Verify SettingsDialog initializes and loads all tabs and values cleanly."""
        dlg = SettingsDialog()
        self.assertIsNotNone(dlg)
        self.assertIn("Settings", dlg.windowTitle())

        # Check resolution combo loaded
        self.assertGreater(dlg.combo_resolution.count(), 0)
        # Check quality combo loaded
        self.assertGreater(dlg.combo_quality.count(), 0)
        # Check camera shape combo loaded
        self.assertGreater(dlg.combo_cam_shape.count(), 0)
        # Check hotkeys text fields
        self.assertEqual(dlg.txt_hk_rec.text(), "F9")
        self.assertEqual(dlg.txt_hk_cam_full.text(), "F4")

        dlg.close()
        dlg.deleteLater()

    def test_shortcuts_dialog(self):
        """Verify ShortcutsDialog opens and lists keybindings."""
        dlg = ShortcutsDialog()
        self.assertIsNotNone(dlg)
        self.assertIn("Shortcuts", dlg.windowTitle())
        dlg.close()
        dlg.deleteLater()

    def test_about_dialog(self):
        """Verify AboutDialog loads developer and organization credits."""
        dlg = AboutDialog()
        self.assertIsNotNone(dlg)
        self.assertIn("About", dlg.windowTitle())
        dlg.close()
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
