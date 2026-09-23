"""
Interactive User Manual & Documentation Dialog for CNAT Screen Recorder.
Features in-app searchable manual viewing, browser launching, and downloadable HTML/Markdown manual exports.
"""

import os
import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QTextDocument
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextBrowser,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from src.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEVELOPER_NAME,
    COMPANY_NAME,
    COMPANY_SHORT,
    COMPANY_WEBSITE,
    COMPANY_PHONE,
    COPYRIGHT_TEXT,
)


class UserManualDialog(QDialog):
    """Modern Glassmorphic Interactive User Manual & Export Dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"User Manual & Documentation - {APP_NAME}")
        self.resize(920, 680)
        self.setMinimumSize(700, 500)
        self.setModal(True)

        self.docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
        self.html_manual_path = self.docs_dir / "USER_MANUAL.html"
        self.md_manual_path = self.docs_dir / "USER_MANUAL.md"

        self._setup_ui()
        self._load_documentation()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. Header with Organization & Software Credentials
        header_card = QFrame(self)
        header_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #161826, stop:1 #23273D);
                border: 1px solid #4F46E5;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(16)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_title = QLabel(f"📖 {APP_NAME.upper()} — Official User Guide")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF; background: transparent;")
        lbl_meta = QLabel(
            f"<span>Developed by <b>{DEVELOPER_NAME}</b> | <b>{COMPANY_NAME} ({COMPANY_SHORT})</b> | 🌐 <a href='{COMPANY_WEBSITE}' style='color: #818CF8; text-decoration: none;'>www.codernaccotax.co.in</a> | 📞 <a href='tel:{COMPANY_PHONE}' style='color: #818CF8; text-decoration: none;'>{COMPANY_PHONE}</a></span>"
        )
        lbl_meta.setStyleSheet("font-size: 11px; color: #9CA3AF; background: transparent;")
        lbl_meta.setOpenExternalLinks(True)
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_meta)
        header_layout.addLayout(title_vbox, 1)

        main_layout.addWidget(header_card)

        # 2. Search & Download Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        # Search box
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("🔍 Search user manual...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #1A1D28;
                border: 1px solid #3F4458;
                border-radius: 8px;
                padding: 6px 12px;
                color: #F9FAFB;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        action_bar.addWidget(self.txt_search, 1)

        # Download / Export HTML Manual
        btn_export_html = QPushButton("💾 Export HTML")
        btn_export_html.setProperty("class", "SmallBtn")
        btn_export_html.setToolTip("Save standalone styled HTML User Manual file to disk")
        btn_export_html.clicked.connect(self._export_html_manual)
        action_bar.addWidget(btn_export_html)

        # Download / Export Markdown Manual
        btn_export_md = QPushButton("📄 Export Markdown")
        btn_export_md.setProperty("class", "SmallBtn")
        btn_export_md.setToolTip("Save complete Markdown User Manual (.md) file to disk")
        btn_export_md.clicked.connect(self._export_md_manual)
        action_bar.addWidget(btn_export_md)

        # Open in Web Browser
        btn_browser = QPushButton("🌐 Open in Browser")
        btn_browser.setProperty("class", "SmallBtn")
        btn_browser.setToolTip("Open user manual in your default web browser for viewing or printing to PDF")
        btn_browser.clicked.connect(self._open_in_browser)
        action_bar.addWidget(btn_browser)

        # Open Docs Folder
        btn_open_folder = QPushButton("📂 Docs Folder")
        btn_open_folder.setProperty("class", "SmallBtn")
        btn_open_folder.setToolTip("Open documentation directory in Windows Explorer")
        btn_open_folder.clicked.connect(self._open_docs_folder)
        action_bar.addWidget(btn_open_folder)

        main_layout.addLayout(action_bar)

        # 3. Interactive Text Browser Display
        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #12141D;
                border: 1px solid #2D3142;
                border-radius: 10px;
                padding: 16px;
                color: #E5E7EB;
                font-size: 13px;
                selection-background-color: #4F46E5;
            }
        """)
        main_layout.addWidget(self.browser, 1)

        # 4. Footer with Close Button
        footer_layout = QHBoxLayout()
        lbl_copy = QLabel(COPYRIGHT_TEXT)
        lbl_copy.setStyleSheet("font-size: 11px; color: #6B7280;")
        footer_layout.addWidget(lbl_copy)
        footer_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)
        main_layout.addLayout(footer_layout)

    def _load_documentation(self):
        """Load HTML documentation into QTextBrowser."""
        if self.html_manual_path.exists():
            try:
                with open(self.html_manual_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                self.browser.setHtml(html_content)
                return
            except Exception as e:
                print(f"[UserManualDialog] Error reading HTML manual: {e}")

        # Fallback to Markdown
        if self.md_manual_path.exists():
            try:
                with open(self.md_manual_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                self.browser.setMarkdown(md_content)
                return
            except Exception as e:
                print(f"[UserManualDialog] Error reading MD manual: {e}")

        self.browser.setHtml("<h2 style='color:#EF4444;'>User Manual Not Found</h2><p>Please check the docs directory.</p>")

    def _on_search_text_changed(self, text: str):
        """Highlight and seek matching query string in documentation."""
        if not text.strip():
            return
        self.browser.find(text)

    def _export_html_manual(self):
        """Save a copy of the HTML user manual to user's desired folder."""
        if not self.html_manual_path.exists():
            QMessageBox.warning(self, "Export Error", "HTML manual source file was not found.")
            return

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Download / Export HTML User Manual",
            str(Path.home() / "Documents" / f"{COMPANY_SHORT}_Screen_Recorder_User_Manual.html"),
            "HTML Files (*.html);;All Files (*.*)",
        )
        if target_path:
            try:
                shutil.copyfile(self.html_manual_path, target_path)
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"User Manual successfully exported to:\n\n{target_path}\n\nYou can open this file in any web browser or print it as PDF.",
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not save file: {e}")

    def _export_md_manual(self):
        """Save a copy of the Markdown user manual to user's desired folder."""
        if not self.md_manual_path.exists():
            QMessageBox.warning(self, "Export Error", "Markdown manual source file was not found.")
            return

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Download / Export Markdown User Manual",
            str(Path.home() / "Documents" / f"{COMPANY_SHORT}_Screen_Recorder_User_Manual.md"),
            "Markdown Files (*.md);;All Files (*.*)",
        )
        if target_path:
            try:
                shutil.copyfile(self.md_manual_path, target_path)
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Markdown User Manual successfully exported to:\n\n{target_path}",
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not save file: {e}")

    def _open_in_browser(self):
        """Launch the styled HTML manual in default system web browser."""
        if self.html_manual_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.html_manual_path)))
        else:
            QMessageBox.warning(self, "File Not Found", "HTML user manual file is missing.")

    def _open_docs_folder(self):
        """Open docs directory in Windows Explorer."""
        if self.docs_dir.exists():
            os.startfile(str(self.docs_dir))
        else:
            QMessageBox.warning(self, "Folder Not Found", "Documentation directory is missing.")
