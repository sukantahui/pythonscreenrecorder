"""
Primary Dashboard and Main Application Window.
"""

import os
import glob
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QUrl, QMimeData
from PyQt6.QtGui import QIcon, QFont, QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QComboBox,
    QSlider,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QButtonGroup,
    QMessageBox,
    QApplication,
    QMenu,
    QScrollArea,
)

from src.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEVELOPER_NAME,
    COMPANY_NAME,
    COMPANY_SHORT,
    COMPANY_WEBSITE,
    COMPANY_PHONE,
    MODE_FULLSCREEN,
    MODE_REGION,
    MODE_WINDOW,
    DEFAULT_OUTPUT_DIR,
    RESOLUTION_PRESETS,
    QUALITY_PROFILES,
    DEFAULT_RESOLUTION,
    DEFAULT_QUALITY,
    COLOR_ACCENT,
    COLOR_DANGER,
    ASPECT_RATIO_PRESETS,
    WEBCAM_SHAPES,
)
from src.config.settings_manager import settings
from src.core.controller import controller
from src.core.audio_capture import AudioCaptureWorker
from src.core.camera_detect import camera_detector
from src.overlays.region_selector import RegionSelectorOverlay
from src.overlays.countdown_overlay import CountdownOverlay
from src.overlays.annotation_canvas import AnnotationCanvas
from src.overlays.webcam_pip import WebcamPiPOverlay
from src.overlays.cursor_effects import CursorEffectsOverlay
from src.overlays.keystroke_hud import KeystrokeHUDOverlay
from src.ui.floating_bar import FloatingBar
from src.ui.settings_dialog import SettingsDialog
from src.ui.shortcuts_dialog import ShortcutsDialog
from src.ui.about_dialog import AboutDialog
from src.ui.preview_dialog import PreviewDialog
from src.services.hotkey_service import hotkey_service
from src.services.tray_service import TrayService
from src.services.post_processor import post_processor


class MainWindow(QMainWindow):
    """Main dashboard window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {COMPANY_NAME} ({COMPANY_SHORT})")
        saved_w = int(settings.get("main_window_width", 860))
        saved_h = int(settings.get("main_window_height", 840))
        self.resize(saved_w, saved_h)
        self.setMinimumSize(720, 600)

        self.controller = controller
        self.selected_mode = MODE_FULLSCREEN
        self.selected_region: Optional[Dict[str, int]] = None
        self._previewing_cam = False

        # Overlays & Toolbars
        self.region_selector = RegionSelectorOverlay()
        self.countdown_overlay = CountdownOverlay()
        self.annotation_canvas = AnnotationCanvas()
        self.webcam_overlay: Optional[WebcamPiPOverlay] = None
        self.cursor_effects = CursorEffectsOverlay()
        self.keystroke_hud = KeystrokeHUDOverlay()
        self.floating_bar = FloatingBar()
        self.tray_service = TrayService(self)

        self._setup_ui()
        self._connect_signals()
        self._refresh_recent_recordings()

        # Start background services
        hotkey_service.start(settings.get("hotkeys"))
        self.tray_service.show()

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 18, 20, 14)
        main_layout.setSpacing(14)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_logo = QLabel(f"🔴 {APP_NAME.upper()}")
        lbl_logo.setStyleSheet("font-size: 15px; font-weight: bold; color: #F9FAFB; letter-spacing: 0.5px;")
        lbl_logo.setMinimumWidth(230)
        lbl_subtitle = QLabel(f"by {COMPANY_NAME} ({COMPANY_SHORT}) • {DEVELOPER_NAME}")
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #818CF8; font-weight: 500;")
        lbl_subtitle.setMinimumWidth(230)
        title_box.addWidget(lbl_logo)
        title_box.addWidget(lbl_subtitle)
        header_layout.addLayout(title_box)

        self.lbl_status = QLabel("● Ready")
        self._set_status("● Ready", "ready")
        header_layout.addWidget(self.lbl_status)
        header_layout.addStretch()

        btn_folder = QPushButton("📁 Recordings")
        btn_folder.setProperty("class", "SmallBtn")
        btn_folder.clicked.connect(lambda: post_processor.open_folder(settings.get("output_dir", DEFAULT_OUTPUT_DIR)))
        header_layout.addWidget(btn_folder)

        btn_shortcuts = QPushButton("⌨️ Shortcuts")
        btn_shortcuts.setProperty("class", "SmallBtn")
        btn_shortcuts.setToolTip("View keyboard shortcuts reference")
        btn_shortcuts.clicked.connect(self._open_shortcuts)
        header_layout.addWidget(btn_shortcuts)

        btn_settings = QPushButton("⚙️ Settings")
        btn_settings.setProperty("class", "SmallBtn")
        btn_settings.clicked.connect(self._open_settings)
        header_layout.addWidget(btn_settings)

        btn_about = QPushButton("ℹ️ About")
        btn_about.setProperty("class", "SmallBtn")
        btn_about.clicked.connect(self._open_about)
        header_layout.addWidget(btn_about)

        main_layout.addLayout(header_layout)

        # 2. Capture Mode Selector & Aspect Ratio Presets
        mode_card = QFrame(self)
        mode_card.setProperty("class", "Card")
        mode_card_layout = QVBoxLayout(mode_card)
        mode_card_layout.setContentsMargins(12, 12, 12, 12)
        mode_card_layout.setSpacing(10)

        # Mode Selection Toggle Buttons Row
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(12)

        self.mode_group = QButtonGroup(self)

        self.btn_mode_full = QPushButton("🖥️ Full Screen")
        self.btn_mode_full.setProperty("class", "ModeBtn")
        self.btn_mode_full.setCheckable(True)
        self.btn_mode_full.setChecked(True)
        self.btn_mode_full.clicked.connect(lambda: self._set_mode(MODE_FULLSCREEN))
        self.mode_group.addButton(self.btn_mode_full)
        mode_layout.addWidget(self.btn_mode_full)

        self.btn_mode_region = QPushButton("🔲 Custom Region")
        self.btn_mode_region.setProperty("class", "ModeBtn")
        self.btn_mode_region.setCheckable(True)
        self.btn_mode_region.clicked.connect(lambda: self._set_mode(MODE_REGION))
        self.mode_group.addButton(self.btn_mode_region)
        mode_layout.addWidget(self.btn_mode_region)

        mode_card_layout.addLayout(mode_layout)

        # Aspect Ratio Presets - 2 Compact Rows for Social Media & Streaming
        presets_r1 = QHBoxLayout()
        presets_r1.setSpacing(6)
        lbl_presets = QLabel("Locked Ratio Presets:")
        lbl_presets.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: bold; margin-right: 4px;")
        presets_r1.addWidget(lbl_presets)

        presets_r2 = QHBoxLayout()
        presets_r2.setSpacing(6)

        self.preset_chips: Dict[str, QPushButton] = {}
        chip_defs = [
            ("9:16", "📱 9:16 Reel", "Instagram Reels, YouTube Shorts, TikTok (9:16)"),
            ("16:9", "🎬 16:9 YouTube", "YouTube & FB Landscape Video (16:9)"),
            ("1:1", "📷 1:1 Square", "Instagram Square Post (1:1)"),
            ("4:5", "🖼️ 4:5 Portrait", "Instagram Portrait Post (4:5)"),
            ("4:3", "📺 4:3 Classic", "Facebook Post & Tablet (4:3)"),
            ("21:9", "🎞️ 21:9 Cinema", "Ultrawide Cinematic (21:9)"),
            ("freeform", "🔓 Freeform", "Unlocked Custom Region"),
        ]

        for i, (key, text, tip) in enumerate(chip_defs):
            btn = QPushButton(text)
            btn.setProperty("class", "PresetChip")
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, k=key: self._on_preset_chip_clicked(k))
            self.preset_chips[key] = btn
            if i < 3:
                presets_r1.addWidget(btn)
            else:
                presets_r2.addWidget(btn)

        presets_r1.addStretch()
        presets_r2.addStretch()
        mode_card_layout.addLayout(presets_r1)
        mode_card_layout.addLayout(presets_r2)

        main_layout.addWidget(mode_card)

        # 3. Audio & Webcam Devices Quick Cards Row
        devices_row = QHBoxLayout()
        devices_row.setSpacing(12)

        # System Audio Card
        self.card_sys = QFrame(self)
        self.card_sys.setProperty("class", "Card")
        sys_layout = QVBoxLayout(self.card_sys)
        sys_layout.setContentsMargins(12, 12, 12, 12)
        self.chk_sys = QCheckBox("🔊 System Audio")
        self.chk_sys.setChecked(settings.get("record_system_audio", True))
        self.chk_sys.toggled.connect(lambda c: settings.set("record_system_audio", c))
        sys_layout.addWidget(self.chk_sys)

        self.vu_sys = QProgressBar()
        self.vu_sys.setRange(0, 100)
        self.vu_sys.setValue(0)
        self.vu_sys.setTextVisible(False)
        sys_layout.addWidget(self.vu_sys)
        devices_row.addWidget(self.card_sys)

        # Microphone Card
        self.card_mic = QFrame(self)
        self.card_mic.setProperty("class", "Card")
        mic_layout = QVBoxLayout(self.card_mic)
        mic_layout.setContentsMargins(12, 12, 12, 12)
        mic_layout.setSpacing(6)
        self.chk_mic = QCheckBox("🎙️ Microphone")
        self.chk_mic.setChecked(settings.get("record_microphone", False))
        self.chk_mic.toggled.connect(lambda c: settings.set("record_microphone", c))
        mic_layout.addWidget(self.chk_mic)

        self.combo_mic_source = QComboBox()
        self.combo_mic_source.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_mic_source.setMinimumContentsLength(8)
        self.combo_mic_source.setToolTip("Select microphone or webcam audio input")
        self.combo_mic_source.currentIndexChanged.connect(self._on_mic_source_changed)
        mic_layout.addWidget(self.combo_mic_source)

        self.vu_mic = QProgressBar()
        self.vu_mic.setRange(0, 100)
        self.vu_mic.setValue(0)
        self.vu_mic.setTextVisible(False)
        mic_layout.addWidget(self.vu_mic)

        # Noise Reduction Slider
        noise_row = QHBoxLayout()
        lbl_noise_title = QLabel("🔇 Noise Reduction:")
        lbl_noise_title.setStyleSheet("font-size: 11px; color: #8e8ea0;")
        self.lbl_noise_val = QLabel("Off")
        self.lbl_noise_val.setStyleSheet("font-size: 11px; color: #8e8ea0; font-weight: bold;")
        noise_row.addWidget(lbl_noise_title)
        noise_row.addStretch()
        noise_row.addWidget(self.lbl_noise_val)
        mic_layout.addLayout(noise_row)

        self.slider_noise = QSlider(Qt.Orientation.Horizontal)
        self.slider_noise.setRange(0, 100)
        curr_noise = int(settings.get("noise_reduction", 0))
        self.slider_noise.setValue(curr_noise)
        self.slider_noise.setToolTip("Filter out background hum, fan hiss, and room noise in real-time (0% = Off)")
        self.slider_noise.valueChanged.connect(self._on_noise_reduction_changed)
        mic_layout.addWidget(self.slider_noise)
        self._update_noise_label(curr_noise)

        devices_row.addWidget(self.card_mic)

        # Webcam Card
        self.card_cam = QFrame(self)
        self.card_cam.setProperty("class", "Card")
        cam_layout = QVBoxLayout(self.card_cam)
        cam_layout.setContentsMargins(12, 12, 12, 12)
        cam_layout.setSpacing(6)

        cam_top_row = QHBoxLayout()
        self.chk_cam = QCheckBox("📷 Webcam PiP")
        self.chk_cam.setChecked(settings.get("webcam_enabled", False))
        self.chk_cam.toggled.connect(self._on_webcam_toggled)
        cam_top_row.addWidget(self.chk_cam)

        self.btn_preview_cam = QPushButton("👁️ PiP")
        self.btn_preview_cam.setProperty("class", "SmallBtn")
        self.btn_preview_cam.setToolTip("Test webcam floating PiP on screen")
        self.btn_preview_cam.clicked.connect(self._toggle_webcam_preview)
        cam_top_row.addWidget(self.btn_preview_cam)

        self.btn_preview_full_cam = QPushButton("⛶ Full")
        self.btn_preview_full_cam.setProperty("class", "SmallBtn")
        self.btn_preview_full_cam.setToolTip("Test Fullscreen / Region Presenter Cam Mode")
        self.btn_preview_full_cam.clicked.connect(self._toggle_webcam_full_preview)
        cam_top_row.addWidget(self.btn_preview_full_cam)
        cam_layout.addLayout(cam_top_row)

        # Camera Device Dropdown
        self.combo_cam_dev = QComboBox()
        self.combo_cam_dev.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_cam_dev.setMinimumContentsLength(8)
        self.combo_cam_dev.currentIndexChanged.connect(self._on_camera_device_changed)
        cam_layout.addWidget(self.combo_cam_dev)

        # Shape Dropdown
        self.combo_cam_shape = QComboBox()
        self.combo_cam_shape.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        for s_key, s_info in WEBCAM_SHAPES.items():
            self.combo_cam_shape.addItem(f"{s_info['icon']} {s_info['name']}", s_key)
        self.combo_cam_shape.currentIndexChanged.connect(self._on_camera_shape_changed)
        cam_layout.addWidget(self.combo_cam_shape)

        # Webcam Audio Checkbox
        self.chk_cam_audio = QCheckBox("🎙️ Webcam Audio")
        self.chk_cam_audio.setToolTip("Capture sound directly from webcam's built-in microphone")
        self.chk_cam_audio.setChecked(settings.get("record_webcam_audio", False))
        self.chk_cam_audio.toggled.connect(self._on_webcam_audio_toggled)
        cam_layout.addWidget(self.chk_cam_audio)

        devices_row.addWidget(self.card_cam, 1)
        devices_row.setStretch(0, 1)
        devices_row.setStretch(1, 1)
        devices_row.setStretch(2, 1)
        main_layout.addLayout(devices_row)

        # Populate camera and audio devices
        self._refresh_camera_list()
        self._refresh_audio_devices()

        # 4. Resolution & Quality Quick Bar
        info_card = QFrame(self)
        info_card.setStyleSheet("background-color: #161820; border: 1px solid #2D313F; border-radius: 10px;")
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(10)

        lbl_res = QLabel("🎯 Resolution:")
        lbl_res.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        info_layout.addWidget(lbl_res)

        self.combo_main_res = QComboBox()
        for res_name in RESOLUTION_PRESETS.keys():
            self.combo_main_res.addItem(res_name)
        self.combo_main_res.setCurrentText(settings.get("resolution", DEFAULT_RESOLUTION))
        self.combo_main_res.currentIndexChanged.connect(self._on_main_res_changed)
        info_layout.addWidget(self.combo_main_res)

        lbl_q_icon = QLabel("💎 Quality:")
        lbl_q_icon.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        info_layout.addWidget(lbl_q_icon)

        self.combo_main_quality = QComboBox()
        for prof in QUALITY_PROFILES.keys():
            self.combo_main_quality.addItem(prof)
        self.combo_main_quality.setCurrentText(settings.get("quality_profile", DEFAULT_QUALITY))
        self.combo_main_quality.currentIndexChanged.connect(self._on_main_quality_changed)
        info_layout.addWidget(self.combo_main_quality)

        self.lbl_fps_info = QLabel(f"⚡ {settings.get('fps', 60)} FPS")
        self.lbl_fps_info.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(self.lbl_fps_info)

        main_layout.addWidget(info_card)

        # 5. Primary Start Record Button
        self.btn_record = QPushButton("● START RECORDING (F9)")
        self.btn_record.setObjectName("BtnStartRecord")
        self.btn_record.clicked.connect(self._toggle_recording)
        main_layout.addWidget(self.btn_record)

        # 6. Recent Recordings List & Quick Actions
        recent_header = QHBoxLayout()
        lbl_recent = QLabel("Recent Recordings")
        lbl_recent.setStyleSheet("font-size: 13px; font-weight: bold; color: #F9FAFB;")
        recent_header.addWidget(lbl_recent)
        recent_header.addStretch()

        btn_refresh_recent = QPushButton("🔄 Refresh")
        btn_refresh_recent.setProperty("class", "SmallBtn")
        btn_refresh_recent.setToolTip("Refresh list of recent recordings")
        btn_refresh_recent.clicked.connect(self._refresh_recent_recordings)
        recent_header.addWidget(btn_refresh_recent)

        btn_open_all = QPushButton("📂 Open Folder")
        btn_open_all.setProperty("class", "SmallBtn")
        btn_open_all.setToolTip("Open recordings folder in Windows Explorer")
        btn_open_all.clicked.connect(lambda: post_processor.open_folder(settings.get("output_dir", DEFAULT_OUTPUT_DIR)))
        recent_header.addWidget(btn_open_all)

        main_layout.addLayout(recent_header)

        self.list_recent = QListWidget(self)
        self.list_recent.setMinimumHeight(130)
        self.list_recent.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_recent.customContextMenuRequested.connect(self._on_recent_context_menu)
        self.list_recent.itemDoubleClicked.connect(self._on_recent_item_double_clicked)
        main_layout.addWidget(self.list_recent, 1)

        # 7. Footer Branding Bar
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 2, 4, 0)
        lbl_footer = QLabel(
            f"<span>Developer: <b>{DEVELOPER_NAME}</b> | <b>{COMPANY_NAME} ({COMPANY_SHORT})</b> | 🌐 <a href='{COMPANY_WEBSITE}' style='color: #818CF8; text-decoration: none;'>www.codernaccotax.co.in</a> | 📞 <a href='tel:{COMPANY_PHONE}' style='color: #818CF8; text-decoration: none;'>{COMPANY_PHONE}</a></span>"
        )
        lbl_footer.setWordWrap(True)
        lbl_footer.setOpenExternalLinks(True)
        lbl_footer.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        footer_layout.addWidget(lbl_footer, 1)
        footer_layout.addStretch()

        btn_footer_about = QPushButton("ℹ️ About")
        btn_footer_about.setProperty("class", "SmallBtn")
        btn_footer_about.clicked.connect(self._open_about)
        footer_layout.addWidget(btn_footer_about)

        main_layout.addLayout(footer_layout)

    def _refresh_camera_list(self):
        """Populate camera devices into dropdown, prioritizing Iriun Webcam by default."""
        self.combo_cam_dev.blockSignals(True)
        self.combo_cam_dev.clear()

        cameras = camera_detector.get_available_cameras()
        saved_id = settings.get("webcam_device_id")
        preferred_cam = camera_detector.get_preferred_camera(prefer_iriun=True)
        default_id = preferred_cam["id"] if preferred_cam else 0
        target_id = default_id if (saved_id is None or saved_id == 0) else saved_id

        selected_idx = 0
        for i, cam in enumerate(cameras):
            self.combo_cam_dev.addItem(f"{cam['name']}", cam["id"])
            if cam["id"] == target_id:
                selected_idx = i

        if self.combo_cam_dev.count() > 0:
            self.combo_cam_dev.setCurrentIndex(selected_idx)
            settings.set("webcam_device_id", self.combo_cam_dev.currentData())
            settings.set("webcam_device_name", self.combo_cam_dev.currentText())
            if hasattr(self, "chk_cam"):
                self.chk_cam.blockSignals(True)
                self.chk_cam.setChecked(settings.get("webcam_enabled", True))
                self.chk_cam.blockSignals(False)

        self.combo_cam_dev.blockSignals(False)

        # Set saved shape (defaults to Circle Bubble)
        saved_shape = settings.get("webcam_shape", "circle")
        shape_idx = self.combo_cam_shape.findData(saved_shape)
        if shape_idx >= 0:
            self.combo_cam_shape.setCurrentIndex(shape_idx)

    def _refresh_audio_devices(self):
        """Populate available microphone & webcam audio devices into dropdown, prioritizing JBL Commercial & Iriun."""
        self.combo_mic_source.blockSignals(True)
        self.combo_mic_source.clear()

        self.combo_mic_source.addItem("🎙️ Default System Microphone", None)

        audio_info = AudioCaptureWorker.get_audio_devices()
        mics = audio_info.get("microphones", [])
        saved_id = settings.get("mic_device_id")
        valid_mic_ids = [m["id"] for m in mics]
        preferred_mic_id = AudioCaptureWorker.get_preferred_mic_device(prefer_iriun=True)

        if saved_id is not None and saved_id not in valid_mic_ids:
            target_id = preferred_mic_id
        else:
            target_id = saved_id if saved_id is not None else preferred_mic_id

        selected_idx = 0
        for i, mic in enumerate(mics):
            is_cam = mic.get("is_webcam", False)
            is_iriun = any(k in mic["name"].lower() for k in ("iriun", "irium"))
            icon_tag = "📷 " if is_cam else "🎙️ "
            suffix = " [Iriun Webcam]" if is_iriun else (" [Webcam]" if is_cam else "")

            clean_name = mic["name"]
            if "@System32" in clean_name:
                import re
                clean = re.sub(r"@System32\\drivers\\[^;]+;", "", clean_name)
                clean = clean.replace("%1", "").replace("%0", "").strip(" ;()")
                clean_name = f"Bluetooth ({clean})" if clean else "Bluetooth Audio"
            elif len(clean_name) > 28:
                clean_name = clean_name[:25] + "..."

            self.combo_mic_source.addItem(f"{icon_tag}{clean_name}{suffix}", mic["id"])
            if target_id is not None and mic["id"] == target_id:
                selected_idx = i + 1

        self.combo_mic_source.setCurrentIndex(selected_idx)
        chosen_mic_id = self.combo_mic_source.currentData()
        settings.set("mic_device_id", chosen_mic_id)

        if hasattr(self, "chk_mic"):
            self.chk_mic.blockSignals(True)
            self.chk_mic.setChecked(settings.get("record_microphone", True) and len(mics) > 0)
            self.chk_mic.blockSignals(False)

        # Auto-match webcam audio device ID for when user decides to enable it
        cam_name = self.combo_cam_dev.currentText() if hasattr(self, "combo_cam_dev") else "Iriun Webcam"
        webcam_mic_id = AudioCaptureWorker.match_webcam_audio(cam_name)
        if webcam_mic_id is not None:
            settings.set("webcam_audio_device_id", webcam_mic_id)

        # Webcam audio is unchecked by default
        rec_cam_audio = settings.get("record_webcam_audio", False)
        if hasattr(self, "chk_cam_audio"):
            self.chk_cam_audio.blockSignals(True)
            self.chk_cam_audio.setChecked(rec_cam_audio)
            self.chk_cam_audio.blockSignals(False)

        self.combo_mic_source.blockSignals(False)

    def _on_mic_source_changed(self, index: int):
        dev_id = self.combo_mic_source.currentData()
        settings.set("mic_device_id", dev_id)

    def _on_noise_reduction_changed(self, value: int):
        self._update_noise_label(value)
        settings.set("noise_reduction", value)
        controller.set_noise_reduction(value)

    def _update_noise_label(self, value: int):
        if value <= 0:
            self.lbl_noise_val.setText("Off")
            self.lbl_noise_val.setStyleSheet("font-size: 11px; color: #8e8ea0; font-weight: bold;")
        elif value <= 35:
            self.lbl_noise_val.setText(f"{value}% (Low)")
            self.lbl_noise_val.setStyleSheet("font-size: 11px; color: #4ade80; font-weight: bold;")
        elif value <= 70:
            self.lbl_noise_val.setText(f"{value}% (Balanced)")
            self.lbl_noise_val.setStyleSheet("font-size: 11px; color: #00ADB5; font-weight: bold;")
        else:
            self.lbl_noise_val.setText(f"{value}% (High)")
            self.lbl_noise_val.setStyleSheet("font-size: 11px; color: #f59e0b; font-weight: bold;")

    def _on_webcam_audio_toggled(self, checked: bool):
        settings.set("record_webcam_audio", checked)
        if checked:
            cam_name = self.combo_cam_dev.currentText()
            webcam_mic_id = AudioCaptureWorker.match_webcam_audio(cam_name)
            if webcam_mic_id is not None:
                settings.set("webcam_audio_device_id", webcam_mic_id)

    def _on_camera_device_changed(self, index: int):
        dev_id = self.combo_cam_dev.currentData()
        if dev_id is not None:
            settings.set("webcam_device_id", dev_id)
            settings.set("webcam_device_name", self.combo_cam_dev.currentText())
            if self.webcam_overlay:
                self.webcam_overlay.switch_device(dev_id)
            if settings.get("record_webcam_audio", False):
                webcam_mic_id = AudioCaptureWorker.match_webcam_audio(self.combo_cam_dev.currentText())
                if webcam_mic_id is not None:
                    settings.set("webcam_audio_device_id", webcam_mic_id)

    def _on_camera_shape_changed(self, index: int):
        shape = self.combo_cam_shape.currentData()
        if shape:
            settings.set("webcam_shape", shape)
            if self.webcam_overlay:
                self.webcam_overlay.set_shape(shape)

    def _on_webcam_toggled(self, checked: bool):
        settings.set("webcam_enabled", checked)
        if not checked and self.webcam_overlay and not self._previewing_cam:
            self.webcam_overlay.stop()
            self.webcam_overlay = None

    def _sync_webcam_shape_ui(self, shape: str):
        """Synchronize UI dropdown when webcam shape changes via context menu or hover pill."""
        idx = self.combo_cam_shape.findData(shape)
        if idx >= 0:
            self.combo_cam_shape.blockSignals(True)
            self.combo_cam_shape.setCurrentIndex(idx)
            self.combo_cam_shape.blockSignals(False)

    def _create_webcam_overlay(self) -> WebcamPiPOverlay:
        """Create and configure a WebcamPiPOverlay instance with active settings and bindings."""
        dev_id = self.combo_cam_dev.currentData() if self.combo_cam_dev.count() > 0 else settings.get("webcam_device_id", 0)
        shape = self.combo_cam_shape.currentData() or settings.get("webcam_shape", "wide")
        size = settings.get("webcam_size", 220)
        mirrored = settings.get("webcam_mirrored", True)
        filter_name = settings.get("webcam_filter", "normal")
        border_theme = settings.get("webcam_border_color", "indigo")

        overlay = WebcamPiPOverlay(
            device_id=dev_id,
            shape=shape,
            size=size,
            mirrored=mirrored,
            filter_name=filter_name,
            border_theme=border_theme,
        )
        overlay.shape_changed.connect(self._sync_webcam_shape_ui)
        overlay.mode_changed.connect(self.floating_bar.update_webcam_mode)
        overlay.mode_changed.connect(self._on_webcam_mode_changed)
        overlay.closed.connect(self._on_webcam_overlay_closed)
        overlay.set_recording_region(self.selected_region)
        return overlay

    def _on_webcam_overlay_closed(self):
        """Handle webcam overlay closed event."""
        self._previewing_cam = False
        self.btn_preview_cam.setText("👁️ PiP")
        if hasattr(self, "btn_preview_full_cam"):
            self.btn_preview_full_cam.setText("⛶ Full")
        self.floating_bar.update_webcam_mode(False)

    def _on_webcam_mode_changed(self, is_fullscreen: bool):
        """Handle webcam overlay switching between PiP and Fullscreen presenter mode."""
        if hasattr(self, "btn_preview_full_cam"):
            self.btn_preview_full_cam.setText("🗗 PiP" if is_fullscreen else "⛶ Full")
        status_msg = "Presenter Mode (Covering Recording Area)" if is_fullscreen else "Floating PiP Mode"
        self.tray_service.show_notification(APP_NAME, f"📷 Webcam: {status_msg}")

    def _toggle_webcam_preview(self):
        """Toggle live on-screen floating PiP preview."""
        if self.webcam_overlay and self.webcam_overlay.isVisible():
            if self.webcam_overlay.is_fullscreen_cam:
                self.webcam_overlay.toggle_fullscreen_cam()
                self.btn_preview_cam.setText("❌ Close PiP")
                if hasattr(self, "btn_preview_full_cam"):
                    self.btn_preview_full_cam.setText("⛶ Full")
            else:
                self.webcam_overlay.stop()
                self.webcam_overlay = None
                self._previewing_cam = False
                self.btn_preview_cam.setText("👁️ PiP")
                if hasattr(self, "btn_preview_full_cam"):
                    self.btn_preview_full_cam.setText("⛶ Full")
        else:
            self.webcam_overlay = self._create_webcam_overlay()
            self.webcam_overlay.start_webcam()
            self._previewing_cam = True
            self.btn_preview_cam.setText("❌ Close PiP")

    def _toggle_webcam_full_preview(self):
        """Toggle live fullscreen/region presenter cam preview."""
        if self.webcam_overlay and self.webcam_overlay.isVisible() and self.webcam_overlay.is_fullscreen_cam:
            self.webcam_overlay.stop()
            self.webcam_overlay = None
            self._previewing_cam = False
            self.btn_preview_cam.setText("👁️ PiP")
            self.btn_preview_full_cam.setText("⛶ Full")
        else:
            if not self.webcam_overlay or not self.webcam_overlay.isVisible():
                self.webcam_overlay = self._create_webcam_overlay()
                self.webcam_overlay.start_webcam()
            if not self.webcam_overlay.is_fullscreen_cam:
                self.webcam_overlay.toggle_fullscreen_cam(self.selected_region)
            self._previewing_cam = True
            self.btn_preview_cam.setText("❌ Close PiP")
            self.btn_preview_full_cam.setText("❌ Close Full")

    def _toggle_webcam_pip(self):
        """Toggle webcam overlay during recording from floating bar or hotkey."""
        if self.webcam_overlay and self.webcam_overlay.isVisible():
            self.webcam_overlay.stop()
            self.webcam_overlay = None
        else:
            self.webcam_overlay = self._create_webcam_overlay()
            self.webcam_overlay.start_webcam()

    def _toggle_webcam_fullscreen(self):
        """Toggle Fullscreen Presenter Mode covering whole recording area / screen."""
        if self.webcam_overlay and self.webcam_overlay.isVisible():
            self.webcam_overlay.toggle_fullscreen_cam(self.selected_region)
        else:
            self.webcam_overlay = self._create_webcam_overlay()
            self.webcam_overlay.start_webcam()
            self.webcam_overlay.toggle_fullscreen_cam(self.selected_region)

    def _on_webcam_size_requested(self, size: int):
        """Handle dynamic webcam resizing mid-recording from toolbar or menu."""
        settings.set("webcam_size", size)
        if self.webcam_overlay:
            if self.webcam_overlay.is_fullscreen_cam:
                self.webcam_overlay.toggle_fullscreen_cam()
            self.webcam_overlay.set_size(size)

    def _on_camera_shape_changed_from_bar(self, shape: str):
        """Handle framing shape change from floating bar."""
        settings.set("webcam_shape", shape)
        if self.webcam_overlay:
            if self.webcam_overlay.is_fullscreen_cam:
                self.webcam_overlay.toggle_fullscreen_cam()
            self.webcam_overlay.set_shape(shape)
        self._sync_webcam_shape_ui(shape)

    def _on_webcam_filter_changed_from_bar(self, filter_name: str):
        """Handle studio filter change from floating bar."""
        settings.set("webcam_filter", filter_name)
        if self.webcam_overlay:
            self.webcam_overlay.set_filter(filter_name)

    def _connect_signals(self):
        # Controller Signals
        controller.state_changed.connect(self._on_state_changed)
        controller.time_updated.connect(self.floating_bar.update_time)
        controller.fps_updated.connect(self.floating_bar.update_fps)
        controller.audio_levels_updated.connect(self._on_audio_levels)
        controller.recording_finished.connect(self._on_recording_finished)
        controller.error_occurred.connect(self._on_error)

        # Region Selector
        self.region_selector.region_selected.connect(self._on_region_selected)
        self.region_selector.cancelled.connect(self._on_region_cancelled)

        # Countdown Overlay
        self.countdown_overlay.finished.connect(self._execute_start_recording)
        self.countdown_overlay.cancelled.connect(self._on_countdown_cancelled)

        # Floating Toolbar Signals
        self.floating_bar.pause_clicked.connect(controller.pause_recording)
        self.floating_bar.resume_clicked.connect(controller.resume_recording)
        self.floating_bar.stop_clicked.connect(controller.stop_recording)
        self.floating_bar.annotate_clicked.connect(self._toggle_annotations)
        self.floating_bar.toggle_webcam_clicked.connect(self._toggle_webcam_pip)
        self.floating_bar.toggle_webcam_fullscreen_clicked.connect(self._toggle_webcam_fullscreen)
        self.floating_bar.webcam_size_changed.connect(self._on_webcam_size_requested)
        self.floating_bar.webcam_shape_changed.connect(self._on_camera_shape_changed_from_bar)
        self.floating_bar.webcam_filter_changed.connect(self._on_webcam_filter_changed_from_bar)
        self.floating_bar.screenshot_clicked.connect(self._take_screenshot)
        self.floating_bar.restore_main_clicked.connect(self._restore_main_window)

        # Hotkeys
        hotkey_service.record_stop_triggered.connect(self._toggle_recording)
        hotkey_service.pause_resume_triggered.connect(self._toggle_pause)
        hotkey_service.annotate_triggered.connect(self._toggle_annotations)
        hotkey_service.toggle_webcam_triggered.connect(self._toggle_webcam_pip)
        hotkey_service.toggle_webcam_fullscreen_triggered.connect(self._toggle_webcam_fullscreen)
        hotkey_service.mute_mic_triggered.connect(self._toggle_mute_mic)
        hotkey_service.screenshot_triggered.connect(self._take_screenshot)

        # Tray
        self.tray_service.show_requested.connect(self._restore_main_window)
        self.tray_service.record_requested.connect(self._toggle_recording)
        self.tray_service.pause_requested.connect(self._toggle_pause)
        self.tray_service.stop_requested.connect(controller.stop_recording)
        self.tray_service.open_folder_requested.connect(lambda: post_processor.open_folder(settings.get("output_dir")))
        self.tray_service.settings_requested.connect(self._open_settings)
        self.tray_service.about_requested.connect(self._open_about)
        self.tray_service.exit_requested.connect(QApplication.instance().quit)

    def _set_mode(self, mode: str):
        self.selected_mode = mode
        if mode == MODE_REGION:
            # Check if any preset chip is already active
            active_key = None
            for key, btn in self.preset_chips.items():
                if btn.isChecked():
                    active_key = key
                    break
            if active_key:
                self.region_selector.open_with_ratio(active_key)
            else:
                self.region_selector.show()
                self.region_selector.raise_()
                self.region_selector.activateWindow()
        else:
            self.selected_region = None
            if self.webcam_overlay:
                self.webcam_overlay.set_recording_region(None)
            for btn in self.preset_chips.values():
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
            self._set_status("● Full Screen", "ready")

    def _on_preset_chip_clicked(self, ratio_key: str):
        """User clicked a preset aspect ratio chip."""
        self.selected_mode = MODE_REGION
        self.btn_mode_region.setChecked(True)

        for key, btn in self.preset_chips.items():
            btn.blockSignals(True)
            btn.setChecked(key == ratio_key)
            btn.blockSignals(False)

        self.region_selector.open_with_ratio(ratio_key)

    def _on_region_selected(self, region: dict):
        self.selected_region = region
        if self.webcam_overlay:
            self.webcam_overlay.set_recording_region(region)

        ratio_key = region.get("ratio_key", "freeform")
        ratio_label = region.get("ratio_label", "")

        for key, btn in self.preset_chips.items():
            btn.blockSignals(True)
            btn.setChecked(key == ratio_key)
            btn.blockSignals(False)

        suffix = f" ({ratio_label})" if ratio_label and ratio_label != "Custom" else ""
        self._set_status(f"● Region: {region['width']}x{region['height']}{suffix}", "region")

    def _on_region_cancelled(self):
        if not self.selected_region:
            self.btn_mode_full.setChecked(True)
            self._set_mode(MODE_FULLSCREEN)

    def _toggle_recording(self):
        if controller.state == "idle":
            self._start_recording_flow()
        elif controller.state in ["recording", "paused"]:
            controller.stop_recording()

    def _toggle_pause(self):
        if controller.state == "recording":
            controller.pause_recording()
        elif controller.state == "paused":
            controller.resume_recording()

    def _start_recording_flow(self):
        if self.selected_mode == MODE_REGION and not self.selected_region:
            self.region_selector.show()
            return

        cd_secs = int(settings.get("countdown_seconds", 3))
        if cd_secs > 0:
            self._set_status(f"● Starting in {cd_secs}s... (Press ESC to cancel)", "paused")
            self.btn_record.setEnabled(False)
            self.countdown_overlay.start_countdown(seconds=cd_secs, region=self.selected_region)
        else:
            self._execute_start_recording()

    def _on_countdown_cancelled(self):
        self.btn_record.setEnabled(True)
        self._set_status("● Ready", "ready")

    def _execute_start_recording(self):
        self.btn_record.setEnabled(True)
        # Start creative overlays
        if settings.get("highlight_clicks", True):
            self.cursor_effects.start()
        if settings.get("show_keystrokes", False):
            self.keystroke_hud.start()

        if self.chk_cam.isChecked():
            if not self.webcam_overlay or not self.webcam_overlay.isVisible():
                self.webcam_overlay = self._create_webcam_overlay()
                self.webcam_overlay.start_webcam()
            else:
                self.webcam_overlay.set_recording_region(self.selected_region)

        # Start controller
        if controller.start_recording(region=self.selected_region):
            if settings.get("minimize_to_tray_on_record", True):
                self.hide()
            self.floating_bar.show()
            if self.webcam_overlay:
                self.floating_bar.update_webcam_mode(self.webcam_overlay.is_fullscreen_cam)
            self.tray_service.set_recording_state(True)
            self.tray_service.show_notification(APP_NAME, "Recording started!")

    def _set_status(self, text: str, status_type: str = "ready"):
        """Update top status pill with dynamic styling."""
        self.lbl_status.setText(text)
        if status_type == "recording":
            self.lbl_status.setStyleSheet("""
                QLabel {
                    color: #EF4444;
                    font-weight: bold;
                    font-size: 11px;
                    background-color: rgba(239, 68, 68, 0.15);
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 12px;
                    padding: 3px 10px;
                }
            """)
        elif status_type == "paused":
            self.lbl_status.setStyleSheet("""
                QLabel {
                    color: #F59E0B;
                    font-weight: bold;
                    font-size: 11px;
                    background-color: rgba(245, 158, 11, 0.15);
                    border: 1px solid rgba(245, 158, 11, 0.4);
                    border-radius: 12px;
                    padding: 3px 10px;
                }
            """)
        elif status_type == "region":
            self.lbl_status.setStyleSheet("""
                QLabel {
                    color: #818CF8;
                    font-weight: bold;
                    font-size: 11px;
                    background-color: rgba(99, 102, 241, 0.15);
                    border: 1px solid rgba(99, 102, 241, 0.4);
                    border-radius: 12px;
                    padding: 3px 10px;
                }
            """)
        else:
            self.lbl_status.setStyleSheet("""
                QLabel {
                    color: #10B981;
                    font-weight: 600;
                    font-size: 11px;
                    background-color: rgba(16, 185, 129, 0.12);
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    border-radius: 12px;
                    padding: 3px 10px;
                }
            """)

    def _on_state_changed(self, state: str):
        if state == "recording":
            self._set_status("● Recording", "recording")
            self.btn_record.setText("⏹ STOP RECORDING (F9)")
            self.btn_record.setStyleSheet("background-color: #EF4444; border-radius: 24px;")
            self.floating_bar.set_paused_state(False)
            self.tray_service.set_recording_state(True, is_paused=False)
        elif state == "paused":
            self._set_status("⏸ Paused", "paused")
            self.btn_record.setText("▶ RESUME RECORDING (F10)")
            self.floating_bar.set_paused_state(True)
            self.tray_service.set_recording_state(True, is_paused=True)
        elif state in ["idle", "finalizing"]:
            self._set_status("● Ready", "ready")
            self.btn_record.setText("● START RECORDING (F9)")
            self.btn_record.setStyleSheet("")
            self.floating_bar.hide()
            self.annotation_canvas.hide()
            self.cursor_effects.stop()
            self.keystroke_hud.stop()
            if self.webcam_overlay and not self._previewing_cam:
                self.webcam_overlay.stop()
                self.webcam_overlay = None
            self.tray_service.set_recording_state(False)

    def _on_audio_levels(self, sys_lvl: float, mic_lvl: float):
        self.vu_sys.setValue(int(sys_lvl * 100))
        self.vu_mic.setValue(int(mic_lvl * 100))

    def _on_recording_finished(self, filepath: str):
        self._refresh_recent_recordings()
        self.tray_service.show_notification(APP_NAME, f"Saved: {os.path.basename(filepath)}")
        self._restore_main_window()

        # Open post-recording preview dialog
        dlg = PreviewDialog(filepath, self)
        dlg.exec()

    def _on_error(self, err: str):
        QMessageBox.critical(self, "Recording Error", err)

    def _toggle_annotations(self):
        if self.annotation_canvas.isVisible():
            self.annotation_canvas.hide()
        else:
            self.annotation_canvas.show()

    def _take_screenshot(self):
        import mss
        from PIL import Image
        from datetime import datetime

        output_dir = settings.get("output_dir", DEFAULT_OUTPUT_DIR)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(output_dir, f"Screenshot_{timestamp}.png")

        with mss.MSS() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            img = sct.grab(mon)
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            pil_img.save(filepath)

        self.tray_service.show_notification("Screenshot Captured", f"Saved to {os.path.basename(filepath)}")
        self._refresh_recent_recordings()

    def _restore_main_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()

    def _on_main_res_changed(self, index: int):
        res = self.combo_main_res.currentText()
        settings.set("resolution", res)

    def _on_main_quality_changed(self, index: int):
        q = self.combo_main_quality.currentText()
        settings.set("quality_profile", q)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            hotkey_service.start(settings.get("hotkeys"))
            self._refresh_camera_list()
            self._refresh_audio_devices()
            self.chk_mic.blockSignals(True)
            self.chk_mic.setChecked(settings.get("record_microphone", False))
            self.chk_mic.blockSignals(False)
            self.chk_cam_audio.blockSignals(True)
            self.chk_cam_audio.setChecked(settings.get("record_webcam_audio", False))
            self.chk_cam_audio.blockSignals(False)
            self.combo_main_res.blockSignals(True)
            self.combo_main_res.setCurrentText(settings.get("resolution", DEFAULT_RESOLUTION))
            self.combo_main_res.blockSignals(False)
            self.combo_main_quality.blockSignals(True)
            self.combo_main_quality.setCurrentText(settings.get("quality_profile", DEFAULT_QUALITY))
            self.combo_main_quality.blockSignals(False)
            self.lbl_fps_info.setText(f"⚡ {settings.get('fps', 60)} FPS")
            noise_val = int(settings.get("noise_reduction", 0))
            self.slider_noise.blockSignals(True)
            self.slider_noise.setValue(noise_val)
            self.slider_noise.blockSignals(False)
            self._update_noise_label(noise_val)

    def _open_shortcuts(self):
        """Open the Keyboard Shortcuts Reference Dialog."""
        dlg = ShortcutsDialog(self)
        dlg.exec()

    def _toggle_mute_mic(self):
        """Hotkey handler to toggle microphone mute status live."""
        current = self.chk_mic.isChecked()
        new_state = not current
        self.chk_mic.setChecked(new_state)
        settings.set("record_microphone", new_state)
        status_text = "Microphone Enabled" if new_state else "Microphone Muted"
        self.tray_service.show_notification(APP_NAME, f"🎙️ {status_text} (F6)")

    def _open_about(self):
        """Open the CNAT Credits & About Dialog."""
        dlg = AboutDialog(self)
        dlg.exec()

    def _refresh_recent_recordings(self):
        self.list_recent.clear()
        output_dir = settings.get("output_dir", DEFAULT_OUTPUT_DIR)
        if not os.path.exists(output_dir):
            return

        files = glob.glob(os.path.join(output_dir, "*.*"))
        video_files = [f for f in files if f.lower().endswith((".mp4", ".mkv", ".webm", ".gif", ".png"))]
        video_files.sort(key=os.path.getmtime, reverse=True)

        if not video_files:
            empty_item = QListWidgetItem("No recordings yet. Hit Record (F9) to start!")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_recent.addItem(empty_item)
            return

        from datetime import datetime
        for vf in video_files[:10]:
            size_mb = os.path.getsize(vf) / (1024 * 1024)
            name = os.path.basename(vf)
            mtime = os.path.getmtime(vf)
            time_str = datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M")
            icon = "🎬" if vf.lower().endswith((".mp4", ".mkv", ".webm")) else ("🎞️" if vf.lower().endswith(".gif") else "📸")
            item = QListWidgetItem(f"{icon}  {name}   [{size_mb:.1f} MB  •  {time_str}]")
            item.setData(Qt.ItemDataRole.UserRole, vf)
            item.setToolTip(f"Path: {vf}\nDouble-click to open/preview\nRight-click for options")
            self.list_recent.addItem(item)

    def _on_recent_item_double_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            if path.lower().endswith((".mp4", ".mkv", ".webm")):
                dlg = PreviewDialog(path, self)
                dlg.exec()
            else:
                post_processor.open_folder(os.path.dirname(path))

    def _on_recent_context_menu(self, pos):
        item = self.list_recent.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.exists(path):
            return

        menu = QMenu(self)
        is_video = path.lower().endswith((".mp4", ".mkv", ".webm"))

        act_play = menu.addAction("▶ Preview / Play" if is_video else "👁️ Open Image")
        act_copy = menu.addAction("📋 Copy File")
        act_reveal = menu.addAction("📂 Reveal in Explorer")
        menu.addSeparator()
        act_del = menu.addAction("🗑️ Delete File")

        action = menu.exec(self.list_recent.mapToGlobal(pos))
        if action == act_play:
            self._on_recent_item_double_clicked(item)
        elif action == act_copy:
            clipboard = QApplication.clipboard()
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(path)])
            mime.setText(path)
            clipboard.setMimeData(mime)
            self.tray_service.show_notification("Copied to Clipboard", os.path.basename(path))
        elif action == act_reveal:
            import subprocess
            try:
                subprocess.run(f'explorer /select,"{os.path.normpath(path)}"', shell=True)
            except Exception:
                post_processor.open_folder(os.path.dirname(path))
        elif action == act_del:
            ret = QMessageBox.question(
                self,
                "Delete Recording",
                f"Are you sure you want to permanently delete:\n{os.path.basename(path)}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(path)
                    self._refresh_recent_recordings()
                except Exception as e:
                    QMessageBox.warning(self, "Delete Failed", f"Could not delete file: {e}")


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.isMaximized() and not self.isMinimized():
            settings.set("main_window_width", self.width())
            settings.set("main_window_height", self.height())

    def closeEvent(self, event):
        if not self.isMaximized() and not self.isMinimized():
            settings.set("main_window_width", self.width())
            settings.set("main_window_height", self.height())
        if controller.state in ["recording", "paused"]:
            ret = QMessageBox.question(
                self,
                "Recording in Progress",
                "Recording is active. Do you want to stop and save before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                controller.stop_recording()
        if self.webcam_overlay:
            self.webcam_overlay.stop()
            self.webcam_overlay = None
        hotkey_service.stop()
        super().closeEvent(event)
