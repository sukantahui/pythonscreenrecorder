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
    FPS_OPTIONS,
    QUALITY_PROFILES,
    FORMAT_MP4,
    FORMAT_MKV,
    FORMAT_WEBM,
)
from src.core.audio_capture import AudioCaptureWorker
from src.core.camera_detect import camera_detector
from src.core.hardware_detect import hardware_detector
from src.services.post_processor import PostProcessor


class SettingsDialog(QDialog):
    """Configuration dialog for audio devices, cameras, encoders, and hotkeys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apex Recorder - Settings")
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
        for mic in devices.get("microphones", []):
            self.combo_mic_dev.addItem(mic["name"], mic["id"])
        mic_form.addRow("Microphone Device:", self.combo_mic_dev)

        self.slider_mic_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_mic_vol.setRange(0, 200)
        self.slider_mic_vol.setValue(100)
        mic_form.addRow("Mic Volume:", self.slider_mic_vol)
        layout.addWidget(grp_mic)

        layout.addStretch()

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
        self.combo_cam_shape.addItem("Circle PiP", "circle")
        self.combo_cam_shape.addItem("Rounded Square PiP", "rounded")
        self.combo_cam_shape.addItem("Square / Rect PiP", "rect")
        cam_form.addRow("Default Shape:", self.combo_cam_shape)

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
        self.txt_hk_snap = QLineEdit("F11")
        hk_form.addRow("Take Screenshot:", self.txt_hk_snap)
        layout.addWidget(grp_hk)

        layout.addStretch()

    def _refresh_camera_devices(self):
        """Populate camera devices dropdown."""
        curr_id = self.combo_cam_dev.currentData() if self.combo_cam_dev.count() > 0 else settings.get("webcam_device_id", 0)
        self.combo_cam_dev.clear()

        cameras = camera_detector.get_available_cameras()
        select_idx = 0
        for i, cam in enumerate(cameras):
            self.combo_cam_dev.addItem(f"{cam['name']} (ID {cam['id']})", cam["id"])
            if cam["id"] == curr_id:
                select_idx = i

        if self.combo_cam_dev.count() > 0:
            self.combo_cam_dev.setCurrentIndex(select_idx)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.txt_output_dir.text())
        if folder:
            self.txt_output_dir.setText(folder)

    def _load_values(self):
        self.txt_output_dir.setText(settings.get("output_dir"))
        self.chk_tray_minimize.setChecked(settings.get("minimize_to_tray_on_record", True))

        self.combo_quality.setCurrentText(settings.get("quality_profile", "High (10 Mbps)"))
        self.combo_format.setCurrentText(settings.get("format", FORMAT_MP4))

        self.chk_sys_audio.setChecked(settings.get("record_system_audio", True))
        self.slider_sys_vol.setValue(int(settings.get("system_audio_volume", 100)))

        self.chk_mic_audio.setChecked(settings.get("record_microphone", False))
        self.slider_mic_vol.setValue(int(settings.get("mic_volume", 100)))

        # Load cameras
        self._refresh_camera_devices()
        shape = settings.get("webcam_shape", "circle")
        idx = self.combo_cam_shape.findData(shape)
        if idx >= 0:
            self.combo_cam_shape.setCurrentIndex(idx)

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
        self.txt_hk_snap.setText(hk.get("screenshot", "F11"))

    def _save_and_close(self):
        settings.set("output_dir", self.txt_output_dir.text())
        settings.set("minimize_to_tray_on_record", self.chk_tray_minimize.isChecked())

        settings.set("quality_profile", self.combo_quality.currentText())
        settings.set("format", self.combo_format.currentText())
        settings.set("fps", self.combo_fps.currentData() or 60)

        settings.set("record_system_audio", self.chk_sys_audio.isChecked())
        settings.set("system_audio_volume", self.slider_sys_vol.value())

        settings.set("record_microphone", self.chk_mic_audio.isChecked())
        settings.set("mic_device_id", self.combo_mic_dev.currentData())
        settings.set("mic_volume", self.slider_mic_vol.value())

        # Save Webcam Settings
        if self.combo_cam_dev.currentData() is not None:
            settings.set("webcam_device_id", self.combo_cam_dev.currentData())
            settings.set("webcam_device_name", self.combo_cam_dev.currentText())
        settings.set("webcam_shape", self.combo_cam_shape.currentData() or "circle")
        settings.set("webcam_size", self.slider_cam_size.value())
        settings.set("webcam_mirrored", self.chk_cam_mirror.isChecked())

        settings.set("show_cursor", self.chk_cursor.isChecked())
        settings.set("highlight_clicks", self.chk_ripples.isChecked())
        settings.set("show_keystrokes", self.chk_keystrokes.isChecked())

        settings.set("hotkeys", {
            "record_stop": self.txt_hk_rec.text().strip(),
            "pause_resume": self.txt_hk_pause.text().strip(),
            "annotate": self.txt_hk_draw.text().strip(),
            "screenshot": self.txt_hk_snap.text().strip(),
        })

        self.accept()
