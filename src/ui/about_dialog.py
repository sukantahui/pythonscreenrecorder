"""
About Dialog presenting software details, developer information, and CNAT branding.
"""

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
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


class AboutDialog(QDialog):
    """Modern Glassmorphic About & Credits Dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About - {APP_NAME}")
        self.setFixedSize(500, 460)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Frame with Gradient Banner
        card_header = QFrame(self)
        card_header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E202E, stop:1 #2D314E);
                border: 1px solid #4F46E5;
                border-radius: 14px;
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout(card_header)
        header_layout.setSpacing(6)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_app = QLabel(f"🔴 {APP_NAME.upper()}")
        lbl_app.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF; letter-spacing: 1px; background: transparent;")
        lbl_app.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_app)

        lbl_ver = QLabel(f"Version {APP_VERSION} • Production Release")
        lbl_ver.setStyleSheet("font-size: 12px; color: #A5B4FC; font-weight: 500; background: transparent;")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_ver)

        layout.addWidget(card_header)

        # Developer & Company Details Card
        card_info = QFrame(self)
        card_info.setProperty("class", "Card")
        info_layout = QVBoxLayout(card_info)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(10)

        # Developer
        lbl_dev = QLabel(f"<b>Developer:</b> &nbsp; {DEVELOPER_NAME}")
        lbl_dev.setStyleSheet("font-size: 13px; color: #F3F4F6;")
        info_layout.addWidget(lbl_dev)

        # Organization
        lbl_org = QLabel(f"<b>Organization:</b> &nbsp; {COMPANY_NAME} ({COMPANY_SHORT})")
        lbl_org.setStyleSheet("font-size: 13px; color: #F3F4F6;")
        info_layout.addWidget(lbl_org)

        # Website Link
        lbl_web = QLabel(
            f"<b>Website:</b> &nbsp; <a href='{COMPANY_WEBSITE}' style='color: #818CF8; text-decoration: none; font-weight: bold;'>{COMPANY_WEBSITE}</a>"
        )
        lbl_web.setOpenExternalLinks(True)
        lbl_web.setStyleSheet("font-size: 13px; color: #F3F4F6;")
        info_layout.addWidget(lbl_web)

        # Phone Link
        lbl_phone = QLabel(
            f"<b>Phone:</b> &nbsp; <a href='tel:{COMPANY_PHONE}' style='color: #818CF8; text-decoration: none; font-weight: bold;'>+91 {COMPANY_PHONE}</a>"
        )
        lbl_phone.setOpenExternalLinks(True)
        lbl_phone.setStyleSheet("font-size: 13px; color: #F3F4F6;")
        info_layout.addWidget(lbl_phone)

        layout.addWidget(card_info)

        # Copyright & Info
        lbl_copy = QLabel(COPYRIGHT_TEXT)
        lbl_copy.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        lbl_copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_copy)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_web = QPushButton("🌐 Visit CNAT Website")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(COMPANY_WEBSITE)))
        btn_layout.addWidget(btn_web)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)
