"""
Primary Dashboard and Main Application Window.
"""

import os
import glob
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QUrl
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
)
from src.config.settings_manager import settings
from src.core.controller import controller
from src.core.audio_capture import AudioCaptureWorker
from src.core.camera_detect import camera_detector
from src.overlays.region_selector import RegionSelectorOverlay
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
        self.setFixedSize(760, 720)

        self.selected_mode = MODE_FULLSCREEN
        self.selected_region: Optional[Dict[str, int]] = None
        self._previewing_cam = False

        # Overlays & Toolbars
        self.region_selector = RegionSelectorOverlay()
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

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        lbl_logo = QLabel(f"🔴 {APP_NAME.upper()}")
        lbl_logo.setStyleSheet("font-size: 16px; font-weight: bold; color: #F9FAFB; letter-spacing: 1px;")
        lbl_subtitle = QLabel(f"by {COMPANY_NAME} ({COMPANY_SHORT}) • {DEVELOPER_NAME}")
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #818CF8; font-weight: 500;")
        title_box.addWidget(lbl_logo)
        title_box.addWidget(lbl_subtitle)
        header_layout.addLayout(title_box)

        self.lbl_status = QLabel("● Ready")
        self.lbl_status.setStyleSheet("color: #10B981; font-weight: 600; font-size: 12px; margin-left: 8px;")
        header_layout.addWidget(self.lbl_status)
        header_layout.addStretch()

        btn_folder = QPushButton("📁 Recordings")
        btn_folder.clicked.connect(lambda: post_processor.open_folder(settings.get("output_dir", DEFAULT_OUTPUT_DIR)))
        header_layout.addWidget(btn_folder)

        btn_shortcuts = QPushButton("⌨️ Shortcuts")
        btn_shortcuts.setToolTip("View keyboard shortcuts reference")
        btn_shortcuts.clicked.connect(self._open_shortcuts)
        header_layout.addWidget(btn_shortcuts)

        btn_settings = QPushButton("⚙️ Settings")
        btn_settings.clicked.connect(self._open_settings)
        header_layout.addWidget(btn_settings)

        btn_about = QPushButton("ℹ️ About")
        btn_about.clicked.connect(self._open_about)
        header_layout.addWidget(btn_about)

        main_layout.addLayout(header_layout)

        # 2. Capture Mode Selector
        mode_card = QFrame(self)
        mode_card.setProperty("class", "Card")
        mode_layout = QHBoxLayout(mode_card)
        mode_layout.setContentsMargins(12, 12, 12, 12)
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

        self.btn_preview_cam = QPushButton("👁️ Preview")
        self.btn_preview_cam.setToolTip("Test webcam video preview on screen")
        self.btn_preview_cam.setFixedHeight(26)
        self.btn_preview_cam.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_preview_cam.clicked.connect(self._toggle_webcam_preview)
        cam_top_row.addWidget(self.btn_preview_cam)
        cam_layout.addLayout(cam_top_row)

        # Camera Device Dropdown
        self.combo_cam_dev = QComboBox()
        self.combo_cam_dev.currentIndexChanged.connect(self._on_camera_device_changed)
        cam_layout.addWidget(self.combo_cam_dev)

        # Shape Dropdown
        self.combo_cam_shape = QComboBox()
        self.combo_cam_shape.addItem("Circle PiP", "circle")
        self.combo_cam_shape.addItem("Rounded PiP", "rounded")
        self.combo_cam_shape.addItem("Rect PiP", "rect")
        self.combo_cam_shape.currentIndexChanged.connect(self._on_camera_shape_changed)
        cam_layout.addWidget(self.combo_cam_shape)

        # Webcam Audio Checkbox
        self.chk_cam_audio = QCheckBox("🎙️ Webcam Audio")
        self.chk_cam_audio.setToolTip("Capture sound directly from webcam's built-in microphone")
        self.chk_cam_audio.setChecked(settings.get("record_webcam_audio", False))
        self.chk_cam_audio.toggled.connect(self._on_webcam_audio_toggled)
        cam_layout.addWidget(self.chk_cam_audio)

        devices_row.addWidget(self.card_cam)
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

        # 6. Recent Recordings List
        lbl_recent = QLabel("Recent Recordings")
        lbl_recent.setStyleSheet("font-size: 14px; font-weight: bold; color: #F9FAFB; margin-top: 4px;")
        main_layout.addWidget(lbl_recent)

        self.list_recent = QListWidget(self)
        self.list_recent.itemDoubleClicked.connect(self._on_recent_item_double_clicked)
        main_layout.addWidget(self.list_recent)

        # 7. Footer Branding Bar
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 2, 4, 0)
        lbl_footer = QLabel(
            f"<span>Developer: <b>{DEVELOPER_NAME}</b> | <b>{COMPANY_NAME} ({COMPANY_SHORT})</b> | 🌐 <a href='{COMPANY_WEBSITE}' style='color: #818CF8; text-decoration: none;'>www.codernaccotax.co.in</a> | 📞 <a href='tel:{COMPANY_PHONE}' style='color: #818CF8; text-decoration: none;'>{COMPANY_PHONE}</a></span>"
        )
        lbl_footer.setOpenExternalLinks(True)
        lbl_footer.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        footer_layout.addWidget(lbl_footer)
        footer_layout.addStretch()

        btn_footer_about = QPushButton("ℹ️ About")
        btn_footer_about.setFixedHeight(24)
        btn_footer_about.setStyleSheet("font-size: 11px; padding: 2px 10px; background-color: #1A1C24;")
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

        self.combo_cam_dev.blockSignals(False)

        # Set saved shape
        saved_shape = settings.get("webcam_shape", "circle")
        shape_idx = self.combo_cam_shape.findData(saved_shape)
        if shape_idx >= 0:
            self.combo_cam_shape.setCurrentIndex(shape_idx)

    def _refresh_audio_devices(self):
        """Populate available microphone & webcam audio devices into dropdown, prioritizing Iriun Webcam."""
        self.combo_mic_source.blockSignals(True)
        self.combo_mic_source.clear()

        self.combo_mic_source.addItem("🎙️ Default System Microphone", None)

        audio_info = AudioCaptureWorker.get_audio_devices()
        mics = audio_info.get("microphones", [])
        saved_id = settings.get("mic_device_id")

        preferred_mic_id = AudioCaptureWorker.get_preferred_mic_device(prefer_iriun=True)
        target_id = saved_id if saved_id is not None else preferred_mic_id

        selected_idx = 0
        for i, mic in enumerate(mics):
            is_cam = mic.get("is_webcam", False)
            is_iriun = any(k in mic["name"].lower() for k in ("iriun", "irium"))
            icon_tag = "📷 " if is_cam else "🎙️ "
            suffix = " [Iriun Webcam]" if is_iriun else (" [Webcam]" if is_cam else "")
            self.combo_mic_source.addItem(f"{icon_tag}{mic['name']}{suffix}", mic["id"])
            if target_id is not None and mic["id"] == target_id:
                selected_idx = i + 1

        self.combo_mic_source.setCurrentIndex(selected_idx)
        chosen_mic_id = self.combo_mic_source.currentData()
        if chosen_mic_id is not None:
            settings.set("mic_device_id", chosen_mic_id)

        # Auto-match webcam audio device ID
        cam_name = self.combo_cam_dev.currentText() if hasattr(self, "combo_cam_dev") else "Iriun Webcam"
        webcam_mic_id = AudioCaptureWorker.match_webcam_audio(cam_name)
        if webcam_mic_id is not None:
            settings.set("webcam_audio_device_id", webcam_mic_id)
            settings.set("record_webcam_audio", True)
            if hasattr(self, "chk_cam_audio"):
                self.chk_cam_audio.blockSignals(True)
                self.chk_cam_audio.setChecked(True)
                self.chk_cam_audio.blockSignals(False)

        self.combo_mic_source.blockSignals(False)

    def _on_mic_source_changed(self, index: int):
        dev_id = self.combo_mic_source.currentData()
        settings.set("mic_device_id", dev_id)

    def _on_noise_reduction_changed(self, value: int):
        self._update_noise_label(value)
        settings.set("noise_reduction", value)
        self.controller.set_noise_reduction(value)

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

    def _toggle_webcam_preview(self):
        """Toggle live on-screen webcam preview."""
        if self.webcam_overlay and self.webcam_overlay.isVisible():
            self.webcam_overlay.stop()
            self.webcam_overlay = None
            self._previewing_cam = False
            self.btn_preview_cam.setText("👁️ Preview")
        else:
            dev_id = self.combo_cam_dev.currentData() if self.combo_cam_dev.count() > 0 else 0
            shape = self.combo_cam_shape.currentData() or "circle"
            size = settings.get("webcam_size", 220)
            mirrored = settings.get("webcam_mirrored", True)

            self.webcam_overlay = WebcamPiPOverlay(
                device_id=dev_id,
                shape=shape,
                size=size,
                mirrored=mirrored
            )
            self.webcam_overlay.start_webcam()
            self._previewing_cam = True
            self.btn_preview_cam.setText("❌ Close Cam")

    def _toggle_webcam_pip(self):
        """Toggle webcam overlay during recording from floating bar."""
        if self.webcam_overlay and self.webcam_overlay.isVisible():
            self.webcam_overlay.stop()
            self.webcam_overlay = None
        else:
            dev_id = settings.get("webcam_device_id", 0)
            shape = settings.get("webcam_shape", "circle")
            size = settings.get("webcam_size", 220)
            mirrored = settings.get("webcam_mirrored", True)

            self.webcam_overlay = WebcamPiPOverlay(
                device_id=dev_id,
                shape=shape,
                size=size,
                mirrored=mirrored
            )
            self.webcam_overlay.start_webcam()

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
        self.region_selector.cancelled.connect(lambda: self._set_mode(MODE_FULLSCREEN))

        # Floating Toolbar Signals
        self.floating_bar.pause_clicked.connect(controller.pause_recording)
        self.floating_bar.resume_clicked.connect(controller.resume_recording)
        self.floating_bar.stop_clicked.connect(controller.stop_recording)
        self.floating_bar.annotate_clicked.connect(self._toggle_annotations)
        self.floating_bar.toggle_webcam_clicked.connect(self._toggle_webcam_pip)
        self.floating_bar.screenshot_clicked.connect(self._take_screenshot)
        self.floating_bar.restore_main_clicked.connect(self._restore_main_window)

        # Hotkeys
        hotkey_service.record_stop_triggered.connect(self._toggle_recording)
        hotkey_service.pause_resume_triggered.connect(self._toggle_pause)
        hotkey_service.annotate_triggered.connect(self._toggle_annotations)
        hotkey_service.toggle_webcam_triggered.connect(self._toggle_webcam_pip)
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
            self.region_selector.show()
        else:
            self.selected_region = None

    def _on_region_selected(self, region: dict):
        self.selected_region = region
        self.lbl_status.setText(f"● Region: {region['width']}x{region['height']}")

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

        # Start creative overlays
        if settings.get("highlight_clicks", True):
            self.cursor_effects.start()
        if settings.get("show_keystrokes", False):
            self.keystroke_hud.start()

        if self.chk_cam.isChecked():
            if not self.webcam_overlay or not self.webcam_overlay.isVisible():
                dev_id = self.combo_cam_dev.currentData() if self.combo_cam_dev.count() > 0 else 0
                shape = self.combo_cam_shape.currentData() or "circle"
                size = settings.get("webcam_size", 220)
                mirrored = settings.get("webcam_mirrored", True)

                self.webcam_overlay = WebcamPiPOverlay(
                    device_id=dev_id,
                    shape=shape,
                    size=size,
                    mirrored=mirrored
                )
                self.webcam_overlay.start_webcam()

        # Start controller
        if controller.start_recording(region=self.selected_region):
            if settings.get("minimize_to_tray_on_record", True):
                self.hide()
            self.floating_bar.show()
            self.tray_service.set_recording_state(True)
            self.tray_service.show_notification(APP_NAME, "Recording started!")

    def _on_state_changed(self, state: str):
        if state == "recording":
            self.lbl_status.setText("● Recording")
            self.lbl_status.setStyleSheet("color: #EF4444; font-weight: bold;")
            self.btn_record.setText("⏹ STOP RECORDING (F9)")
            self.btn_record.setStyleSheet("background-color: #EF4444; border-radius: 24px;")
            self.floating_bar.set_paused_state(False)
            self.tray_service.set_recording_state(True, is_paused=False)
        elif state == "paused":
            self.lbl_status.setText("⏸ Paused")
            self.lbl_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
            self.btn_record.setText("▶ RESUME RECORDING (F10)")
            self.floating_bar.set_paused_state(True)
            self.tray_service.set_recording_state(True, is_paused=True)
        elif state in ["idle", "finalizing"]:
            self.lbl_status.setText("● Ready")
            self.lbl_status.setStyleSheet("color: #10B981; font-weight: bold;")
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

        for vf in video_files[:10]:
            size_mb = os.path.getsize(vf) / (1024 * 1024)
            name = os.path.basename(vf)
            icon = "🎬" if vf.lower().endswith((".mp4", ".mkv", ".webm")) else ("🎞️" if vf.lower().endswith(".gif") else "📸")
            item = QListWidgetItem(f"{icon}  {name}  ({size_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, vf)
            self.list_recent.addItem(item)

    def _on_recent_item_double_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            if path.lower().endswith((".mp4", ".mkv", ".webm")):
                dlg = PreviewDialog(path, self)
                dlg.exec()
            else:
                post_processor.open_folder(os.path.dirname(path))

    def closeEvent(self, event):
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
