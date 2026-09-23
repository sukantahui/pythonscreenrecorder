"""
Settings and configuration modal dialog.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QSlider,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QLineEdit,
)
from src.config.settings_manager import settings
from src.config.constants import (
    APP_NAME,
    FPS_OPTIONS,
    QUALITY_PROFILES,
    DEFAULT_QUALITY,
    RESOLUTION_PRESETS,
    DEFAULT_RESOLUTION,
    DEFAULT_OUTPUT_DIR,
    FORMAT_MP4,
    FORMAT_MKV,
    FORMAT_WEBM,
    WEBCAM_SHAPES,
    WEBCAM_FILTERS,
    WEBCAM_BORDER_THEMES,
)
from src.core.audio_capture import AudioCaptureWorker
from src.core.camera_detect import camera_detector
from src.core.hardware_detect import hardware_detector
from src.services.post_processor import PostProcessor
from src.ui.about_dialog import AboutDialog


class SettingsDialog(QDialog):
    """Configuration dialog for audio devices, cameras, encoders, and hotkeys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Settings")
        self.setFixedSize(560, 520)
        self.setModal(True)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # Tabs
        self.tab_general = QWidget()
        self.tab_video = QWidget()
        self.tab_audio = QWidget()
        self.tab_webcam_overlays = QWidget()
        self.tab_hotkeys = QWidget()

        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_video, "Video & Codec")
        self.tabs.addTab(self.tab_audio, "Audio Devices")
        self.tabs.addTab(self.tab_webcam_overlays, "Webcam & Overlays")
        self.tabs.addTab(self.tab_hotkeys, "Hotkeys")

        self._setup_general_tab()
        self._setup_video_tab()
        self._setup_audio_tab()
        self._setup_webcam_overlays_tab()
        self._setup_hotkeys_tab()

        # Bottom Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_about = QPushButton("ℹ️ About CNAT")
        btn_about.clicked.connect(lambda: AboutDialog(self).exec())
        btn_layout.addWidget(btn_about)

        btn_open_folder = QPushButton("📂 Open Videos Folder")
        btn_open_folder.clicked.connect(lambda: PostProcessor.open_folder(self.txt_output_dir.text()))
        btn_layout.addWidget(btn_open_folder)

        btn_close = QPushButton("Done")
        btn_close.clicked.connect(self._save_and_close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _setup_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
        layout.setSpacing(12)

        # Output Folder Group
        grp_dir = QGroupBox("Storage & Output")
        dir_layout = QVBoxLayout(grp_dir)

        lbl = QLabel("Recordings Directory:")
        dir_layout.addWidget(lbl)

        row = QHBoxLayout()
        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setReadOnly(True)
        row.addWidget(self.txt_output_dir)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_folder)
        row.addWidget(btn_browse)
        dir_layout.addLayout(row)
        layout.addWidget(grp_dir)

        # Recording Behavior Group
        grp_behavior = QGroupBox("Behavior")
        beh_layout = QFormLayout(grp_behavior)

        self.combo_countdown = QComboBox()
        self.combo_countdown.addItems(["No Countdown (0s)", "3 Seconds", "5 Seconds"])
        beh_layout.addRow("Countdown Timer:", self.combo_countdown)

        self.chk_tray_minimize = QCheckBox("Minimize to system tray when recording starts")
        beh_layout.addRow("", self.chk_tray_minimize)

        layout.addWidget(grp_behavior)
        layout.addStretch()

    def _setup_video_tab(self):
        layout = QVBoxLayout(self.tab_video)
        layout.setSpacing(12)

        grp_enc = QGroupBox("Encoding & Hardware Acceleration")
        form = QFormLayout(grp_enc)

        self.combo_encoder = QComboBox()
        self.combo_encoder.addItem("Auto (Best Hardware GPU)", "auto")
        for enc in hardware_detector.get_available_encoders():
            self.combo_encoder.addItem(f"{enc.upper()} Encoder", enc)
        form.addRow("Video Encoder:", self.combo_encoder)

        self.combo_resolution = QComboBox()
        for res_name in RESOLUTION_PRESETS.keys():
            self.combo_resolution.addItem(res_name)
        form.addRow("Recording Resolution:", self.combo_resolution)

        self.combo_quality = QComboBox()
        for prof in QUALITY_PROFILES.keys():
            self.combo_quality.addItem(prof)
        form.addRow("Quality Profile:", self.combo_quality)

        self.combo_fps = QComboBox()
        for fps in FPS_OPTIONS:
            self.combo_fps.addItem(f"{fps} FPS", fps)
        form.addRow("Target Framerate:", self.combo_fps)

        self.combo_format = QComboBox()
        self.combo_format.addItems([FORMAT_MP4, FORMAT_MKV, FORMAT_WEBM])
        form.addRow("Container Format:", self.combo_format)

        layout.addWidget(grp_enc)
        layout.addStretch()

    def _setup_audio_tab(self):
        layout = QVBoxLayout(self.tab_audio)
        layout.setSpacing(12)

        devices = AudioCaptureWorker.get_audio_devices()

        # System Audio
        grp_sys = QGroupBox("System Audio")
        sys_form = QFormLayout(grp_sys)
        self.chk_sys_audio = QCheckBox("Record System Sounds (WASAPI Loopback)")
        sys_form.addRow(self.chk_sys_audio)

        self.slider_sys_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_sys_vol.setRange(0, 150)
        self.slider_sys_vol.setValue(100)
        sys_form.addRow("System Volume:", self.slider_sys_vol)
        layout.addWidget(grp_sys)

        # Microphone Audio
        grp_mic = QGroupBox("Microphone Input")
        mic_form = QFormLayout(grp_mic)
        self.chk_mic_audio = QCheckBox("Record Microphone")
        mic_form.addRow(self.chk_mic_audio)

        self.combo_mic_dev = QComboBox()
        self.combo_mic_dev.addItem("Default System Microphone", None)
        for mic in devices.get("microphones", []):
            tag = " 📷 [Webcam]" if mic.get("is_webcam", False) else ""
            self.combo_mic_dev.addItem(f"{mic['name']}{tag}", mic["id"])
        mic_form.addRow("Microphone Device:", self.combo_mic_dev)

        self.slider_mic_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_mic_vol.setRange(0, 200)
        self.slider_mic_vol.setValue(100)
        mic_form.addRow("Mic Volume:", self.slider_mic_vol)
        layout.addWidget(grp_mic)

        # Webcam Audio
        grp_cam_audio = QGroupBox("Webcam Audio Input")
        cam_audio_form = QFormLayout(grp_cam_audio)
        self.chk_webcam_audio = QCheckBox("Capture Webcam Built-In Microphone")
        cam_audio_form.addRow(self.chk_webcam_audio)

        self.combo_webcam_audio_dev = QComboBox()
        self.combo_webcam_audio_dev.addItem("Auto-Detect from Active Webcam", None)
        for mic in devices.get("webcam_microphones", []):
            self.combo_webcam_audio_dev.addItem(f"📷 {mic['name']}", mic["id"])
        cam_audio_form.addRow("Webcam Audio Device:", self.combo_webcam_audio_dev)

        self.slider_webcam_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_webcam_vol.setRange(0, 200)
        self.slider_webcam_vol.setValue(100)
        cam_audio_form.addRow("Webcam Volume:", self.slider_webcam_vol)
        layout.addWidget(grp_cam_audio)

        # Noise Suppression / Reduction
        grp_noise = QGroupBox("Noise Reduction & Audio Filters")
        noise_form = QFormLayout(grp_noise)

        noise_row = QHBoxLayout()
        self.slider_noise_reduction = QSlider(Qt.Orientation.Horizontal)
        self.slider_noise_reduction.setRange(0, 100)
        self.slider_noise_reduction.setValue(0)
        self.lbl_noise_val = QLabel("Off (0%)")
        self.lbl_noise_val.setStyleSheet("font-weight: bold; color: #8e8ea0; min-width: 100px;")
        self.slider_noise_reduction.valueChanged.connect(self._on_noise_slider_changed)

        noise_row.addWidget(self.slider_noise_reduction, 1)
        noise_row.addWidget(self.lbl_noise_val)
        noise_form.addRow("Noise Suppression:", noise_row)

        lbl_hint = QLabel("Filters background fan hiss, room hum, and mic noise in real-time.")
        lbl_hint.setStyleSheet("font-size: 11px; color: #8e8ea0;")
        noise_form.addRow("", lbl_hint)
        layout.addWidget(grp_noise)

        layout.addStretch()

    def _on_noise_slider_changed(self, val: int):
        self._update_noise_label(val)

    def _update_noise_label(self, val: int):
        if val <= 0:
            self.lbl_noise_val.setText("Off (0%)")
            self.lbl_noise_val.setStyleSheet("font-weight: bold; color: #8e8ea0; min-width: 100px;")
        elif val <= 35:
            self.lbl_noise_val.setText(f"{val}% (Low)")
            self.lbl_noise_val.setStyleSheet("font-weight: bold; color: #4ade80; min-width: 100px;")
        elif val <= 70:
            self.lbl_noise_val.setText(f"{val}% (Balanced)")
            self.lbl_noise_val.setStyleSheet("font-weight: bold; color: #00ADB5; min-width: 100px;")
        else:
            self.lbl_noise_val.setText(f"{val}% (Aggressive)")
            self.lbl_noise_val.setStyleSheet("font-weight: bold; color: #f59e0b; min-width: 100px;")

    def _setup_webcam_overlays_tab(self):
        layout = QVBoxLayout(self.tab_webcam_overlays)
        layout.setSpacing(12)

        # Webcam Device & PiP Group
        grp_cam = QGroupBox("Webcam & Picture-in-Picture (PiP)")
        cam_form = QFormLayout(grp_cam)

        cam_dev_row = QHBoxLayout()
        self.combo_cam_dev = QComboBox()
        cam_dev_row.addWidget(self.combo_cam_dev, 1)

        btn_refresh_cam = QPushButton("🔄")
        btn_refresh_cam.setToolTip("Refresh connected cameras")
        btn_refresh_cam.setFixedWidth(36)
        btn_refresh_cam.clicked.connect(self._refresh_camera_devices)
        cam_dev_row.addWidget(btn_refresh_cam)
        cam_form.addRow("Camera Device:", cam_dev_row)

        self.combo_cam_shape = QComboBox()
        for s_key, s_info in WEBCAM_SHAPES.items():
            self.combo_cam_shape.addItem(f"{s_info['icon']} {s_info['name']}", s_key)
        cam_form.addRow("Default Shape:", self.combo_cam_shape)

        self.combo_cam_filter = QComboBox()
        for f_key, f_info in WEBCAM_FILTERS.items():
            self.combo_cam_filter.addItem(f"{f_info['icon']} {f_info['name']}", f_key)
        cam_form.addRow("Lighting / Filter:", self.combo_cam_filter)

        self.combo_cam_border = QComboBox()
        for b_key, b_info in WEBCAM_BORDER_THEMES.items():
            self.combo_cam_border.addItem(b_info["name"], b_key)
        cam_form.addRow("Border Theme:", self.combo_cam_border)

        # PiP Size Slider
        size_row = QHBoxLayout()
        self.slider_cam_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_cam_size.setRange(120, 380)
        self.slider_cam_size.setValue(220)
        self.lbl_cam_size_val = QLabel("220 px")
        self.slider_cam_size.valueChanged.connect(
            lambda v: self.lbl_cam_size_val.setText(f"{v} px")
        )
        size_row.addWidget(self.slider_cam_size)
        size_row.addWidget(self.lbl_cam_size_val)
        cam_form.addRow("Default PiP Size:", size_row)

        self.chk_cam_mirror = QCheckBox("Flip / Mirror camera feed horizontally")
        cam_form.addRow("", self.chk_cam_mirror)

        self.chk_cam_record_audio = QCheckBox("Capture sound from this webcam during recording")
        self.chk_cam_record_audio.toggled.connect(
            lambda checked: self.chk_webcam_audio.setChecked(checked)
        )
        self.chk_webcam_audio.toggled.connect(
            lambda checked: self.chk_cam_record_audio.setChecked(checked)
        )
        cam_form.addRow("", self.chk_cam_record_audio)

        layout.addWidget(grp_cam)

        # Cursor & Overlay Effects Group
        grp_ov = QGroupBox("Cursor & Visual Effects")
        ov_layout = QVBoxLayout(grp_ov)
        self.chk_cursor = QCheckBox("Show Mouse Cursor in Recording")
        ov_layout.addWidget(self.chk_cursor)
        self.chk_ripples = QCheckBox("Show Animated Mouse Click Ripples")
        ov_layout.addWidget(self.chk_ripples)
        self.chk_keystrokes = QCheckBox("Show Pressed Keystrokes HUD (Keycast)")
        ov_layout.addWidget(self.chk_keystrokes)
        layout.addWidget(grp_ov)

        layout.addStretch()

    def _setup_hotkeys_tab(self):
        layout = QVBoxLayout(self.tab_hotkeys)
        layout.setSpacing(12)

        grp_hk = QGroupBox("Global Hotkeys")
        hk_form = QFormLayout(grp_hk)
        self.txt_hk_rec = QLineEdit("F9")
        hk_form.addRow("Start / Stop Recording:", self.txt_hk_rec)
        self.txt_hk_pause = QLineEdit("F10")
        hk_form.addRow("Pause / Resume:", self.txt_hk_pause)
        self.txt_hk_draw = QLineEdit("F8")
        hk_form.addRow("Toggle Annotations:", self.txt_hk_draw)
        self.txt_hk_cam = QLineEdit("F7")
        hk_form.addRow("Toggle Webcam PiP:", self.txt_hk_cam)
        self.txt_hk_cam_full = QLineEdit("F4")
        hk_form.addRow("Toggle Fullscreen Cam:", self.txt_hk_cam_full)
        self.txt_hk_mic = QLineEdit("F6")
        hk_form.addRow("Mute / Unmute Mic:", self.txt_hk_mic)
        self.txt_hk_snap = QLineEdit("F11")
        hk_form.addRow("Take Screenshot:", self.txt_hk_snap)
        layout.addWidget(grp_hk)

        layout.addStretch()

    def _refresh_camera_devices(self):
        """Populate camera devices dropdown, prioritizing Iriun Webcam by default."""
        cameras = camera_detector.get_available_cameras()
        saved_id = settings.get("webcam_device_id")
        preferred_cam = camera_detector.get_preferred_camera(prefer_iriun=True)
        default_id = preferred_cam["id"] if preferred_cam else 0
        target_id = default_id if (saved_id is None or saved_id == 0) else saved_id

        self.combo_cam_dev.clear()
        select_idx = 0
        for i, cam in enumerate(cameras):
            self.combo_cam_dev.addItem(f"{cam['name']} (ID {cam['id']})", cam["id"])
            if cam["id"] == target_id:
                select_idx = i

        if self.combo_cam_dev.count() > 0:
            self.combo_cam_dev.setCurrentIndex(select_idx)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.txt_output_dir.text())
        if folder:
            self.txt_output_dir.setText(folder)

    def _load_values(self):
        self.txt_output_dir.setText(settings.get("output_dir", DEFAULT_OUTPUT_DIR))
        self.chk_tray_minimize.setChecked(settings.get("minimize_to_tray_on_record", True))

        self.combo_resolution.setCurrentText(settings.get("resolution", DEFAULT_RESOLUTION))
        self.combo_quality.setCurrentText(settings.get("quality_profile", DEFAULT_QUALITY))
        self.combo_format.setCurrentText(settings.get("format", FORMAT_MP4))

        self.chk_sys_audio.setChecked(settings.get("record_system_audio", True))
        self.slider_sys_vol.setValue(int(settings.get("system_audio_volume", 100)))

        self.chk_mic_audio.setChecked(settings.get("record_microphone", True))
        self.slider_mic_vol.setValue(int(settings.get("mic_volume", 100)))
        saved_mic_id = settings.get("mic_device_id")
        preferred_mic_id = AudioCaptureWorker.get_preferred_mic_device(prefer_iriun=True)
        target_mic_id = saved_mic_id if saved_mic_id is not None else preferred_mic_id
        if target_mic_id is not None:
            idx = self.combo_mic_dev.findData(target_mic_id)
            if idx >= 0:
                self.combo_mic_dev.setCurrentIndex(idx)

        # Load webcam audio
        rec_cam_audio = settings.get("record_webcam_audio", False)
        self.chk_webcam_audio.setChecked(rec_cam_audio)
        self.chk_cam_record_audio.setChecked(rec_cam_audio)
        self.slider_webcam_vol.setValue(int(settings.get("webcam_audio_volume", 100)))
        saved_cam_audio_id = settings.get("webcam_audio_device_id")
        if saved_cam_audio_id is not None:
            idx = self.combo_webcam_audio_dev.findData(saved_cam_audio_id)
            if idx >= 0:
                self.combo_webcam_audio_dev.setCurrentIndex(idx)

        # Load noise reduction
        noise_val = int(settings.get("noise_reduction", 0))
        self.slider_noise_reduction.setValue(noise_val)
        self._update_noise_label(noise_val)

        # Load cameras
        self._refresh_camera_devices()
        shape = settings.get("webcam_shape", "wide")
        if shape == "rect":
            shape = "wide"
        idx = self.combo_cam_shape.findData(shape)
        if idx >= 0:
            self.combo_cam_shape.setCurrentIndex(idx)

        filter_name = settings.get("webcam_filter", "normal")
        f_idx = self.combo_cam_filter.findData(filter_name)
        if f_idx >= 0:
            self.combo_cam_filter.setCurrentIndex(f_idx)

        border_theme = settings.get("webcam_border_color", "indigo")
        b_idx = self.combo_cam_border.findData(border_theme)
        if b_idx >= 0:
            self.combo_cam_border.setCurrentIndex(b_idx)

        size = settings.get("webcam_size", 220)
        self.slider_cam_size.setValue(size)
        self.lbl_cam_size_val.setText(f"{size} px")

        self.chk_cam_mirror.setChecked(settings.get("webcam_mirrored", True))

        self.chk_cursor.setChecked(settings.get("show_cursor", True))
        self.chk_ripples.setChecked(settings.get("highlight_clicks", True))
        self.chk_keystrokes.setChecked(settings.get("show_keystrokes", False))

        hk = settings.get("hotkeys", {})
        self.txt_hk_rec.setText(hk.get("record_stop", "F9"))
        self.txt_hk_pause.setText(hk.get("pause_resume", "F10"))
        self.txt_hk_draw.setText(hk.get("annotate", "F8"))
        self.txt_hk_cam.setText(hk.get("toggle_webcam", "F7"))
        self.txt_hk_cam_full.setText(hk.get("toggle_webcam_fullscreen", "F4"))
        self.txt_hk_mic.setText(hk.get("mute_mic", "F6"))
        self.txt_hk_snap.setText(hk.get("screenshot", "F11"))

    def _save_and_close(self):
        settings.set("output_dir", self.txt_output_dir.text())
        settings.set("minimize_to_tray_on_record", self.chk_tray_minimize.isChecked())

        settings.set("resolution", self.combo_resolution.currentText())
        settings.set("quality_profile", self.combo_quality.currentText())
        settings.set("format", self.combo_format.currentText())
        settings.set("fps", self.combo_fps.currentData() or 60)

        settings.set("record_system_audio", self.chk_sys_audio.isChecked())
        settings.set("system_audio_volume", self.slider_sys_vol.value())

        settings.set("record_microphone", self.chk_mic_audio.isChecked())
        settings.set("mic_device_id", self.combo_mic_dev.currentData())
        settings.set("mic_volume", self.slider_mic_vol.value())

        settings.set("record_webcam_audio", self.chk_webcam_audio.isChecked())
        settings.set("webcam_audio_device_id", self.combo_webcam_audio_dev.currentData())
        settings.set("webcam_audio_volume", self.slider_webcam_vol.value())
        settings.set("noise_reduction", self.slider_noise_reduction.value())

        # Save Webcam Settings
        if self.combo_cam_dev.currentData() is not None:
            settings.set("webcam_device_id", self.combo_cam_dev.currentData())
            settings.set("webcam_device_name", self.combo_cam_dev.currentText())
        settings.set("webcam_shape", self.combo_cam_shape.currentData() or "wide")
        settings.set("webcam_filter", self.combo_cam_filter.currentData() or "normal")
        settings.set("webcam_border_color", self.combo_cam_border.currentData() or "indigo")
        settings.set("webcam_size", self.slider_cam_size.value())
        settings.set("webcam_mirrored", self.chk_cam_mirror.isChecked())

        settings.set("show_cursor", self.chk_cursor.isChecked())
        settings.set("highlight_clicks", self.chk_ripples.isChecked())
        settings.set("show_keystrokes", self.chk_keystrokes.isChecked())

        settings.set("hotkeys", {
            "record_stop": self.txt_hk_rec.text().strip(),
            "pause_resume": self.txt_hk_pause.text().strip(),
            "annotate": self.txt_hk_draw.text().strip(),
            "toggle_webcam": self.txt_hk_cam.text().strip(),
            "toggle_webcam_fullscreen": self.txt_hk_cam_full.text().strip(),
            "mute_mic": self.txt_hk_mic.text().strip(),
            "screenshot": self.txt_hk_snap.text().strip(),
        })

        self.accept()
