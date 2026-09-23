"""
Unit tests for UserManualDialog and Documentation Files.
"""

import sys
import os
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.manual_dialog import UserManualDialog
from src.config.constants import (
    APP_NAME,
    DEVELOPER_NAME,
    COMPANY_NAME,
    COMPANY_SHORT,
    COMPANY_WEBSITE,
    COMPANY_PHONE,
)


class TestDocumentationAndManualDialog(unittest.TestCase):
    """Verify documentation file integrity and UserManualDialog functionality."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.project_root = Path(__file__).resolve().parent.parent

    def test_documentation_files_exist(self):
        """Verify that official documentation files exist and are populated."""
        md_manual = self.project_root / "docs" / "USER_MANUAL.md"
        html_manual = self.project_root / "docs" / "USER_MANUAL.html"
        user_guide = self.project_root / "USER_GUIDE.md"
        readme = self.project_root / "README.md"

        self.assertTrue(md_manual.exists(), "docs/USER_MANUAL.md must exist")
        self.assertTrue(html_manual.exists(), "docs/USER_MANUAL.html must exist")
        self.assertTrue(user_guide.exists(), "USER_GUIDE.md must exist")
        self.assertTrue(readme.exists(), "README.md must exist")

        md_content = md_manual.read_text(encoding="utf-8")
        html_content = html_manual.read_text(encoding="utf-8")

        # Verify Organization and Developer Details in documentation
        for content, name in [(md_content, "USER_MANUAL.md"), (html_content, "USER_MANUAL.html")]:
            self.assertIn(COMPANY_NAME, content, f"{name} must contain company name")
            self.assertIn(DEVELOPER_NAME, content, f"{name} must contain developer name")
            self.assertIn(COMPANY_WEBSITE, content, f"{name} must contain website link")
            self.assertIn(COMPANY_PHONE, content, f"{name} must contain phone number")
            self.assertIn("4K Ultra HD", content, f"{name} must cover 4K resolution")
            self.assertIn("F9", content, f"{name} must mention F9 hotkey")

    def test_manual_dialog_instantiation_and_search(self):
        """Verify that UserManualDialog loads HTML content properly and handles searches."""
        dialog = UserManualDialog()
        self.assertIsNotNone(dialog)
        self.assertIn("User Manual", dialog.windowTitle())

        # Verify browser has content loaded
        text = dialog.browser.toPlainText()
        self.assertTrue(len(text) > 500, "UserManualDialog must have loaded text content")
        self.assertIn(COMPANY_NAME, text)

        # Test search
        dialog.txt_search.setText("4K Ultra HD")
        dialog._on_search_text_changed("4K Ultra HD")

        dialog.close()


if __name__ == "__main__":
    unittest.main()
