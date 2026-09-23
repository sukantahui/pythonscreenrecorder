"""
Post-recording video player, trimmer, and export manager dialog.
Features synchronized audio & video playback via QtMultimedia, timeline scrubbing,
volume control, video trimming, GIF creation, and MP3 extraction.
"""

import os
from PyQt6.QtCore import Qt, QUrl, QTimer, QMimeData
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QDoubleSpinBox,
    QMessageBox,
    QFrame,
    QComboBox,
    QApplication,
)
from src.services.post_processor import post_processor


class PreviewDialog(QDialog):
    """Instant audio & video playback, trimmer, and format exporter for recorded clips."""

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setWindowTitle(f"Recording Complete - {os.path.basename(video_path)}")
        self.resize(800, 600)
        self.setMinimumSize(600, 480)
        self.setModal(True)

        self.duration_ms = 0
        self._slider_dragging = False

        # Media Player, Audio Output & Video Output
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(1.0)
        self.player.setAudioOutput(self.audio_output)

        self._setup_ui()
        self._connect_signals()

        # Load video into player
        abs_path = os.path.abspath(self.video_path)
        self.player.setSource(QUrl.fromLocalFile(abs_path))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 1. Video Display Widget
        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 8px;")
        self.video_widget.setMinimumHeight(330)
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)

        # 2. Timeline Scrubber Bar
        scrub_layout = QHBoxLayout()
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #9CA3AF; font-size: 11px; min-width: 85px;")
        scrub_layout.addWidget(self.lbl_time)

        self.slider_timeline = QSlider(Qt.Orientation.Horizontal)
        self.slider_timeline.setRange(0, 1000)
        self.slider_timeline.setValue(0)
        self.slider_timeline.sliderPressed.connect(self._on_slider_pressed)
        self.slider_timeline.sliderMoved.connect(self._on_slider_moved)
        self.slider_timeline.sliderReleased.connect(self._on_slider_released)
        scrub_layout.addWidget(self.slider_timeline)
        layout.addLayout(scrub_layout)

        # 3. Playback, Volume & Trimmer Controls Row
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # Play / Pause
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedWidth(85)
        self.btn_play.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self.btn_play)

        # Volume Controls
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedWidth(36)
        self.btn_mute.setToolTip("Mute / Unmute Audio")
        self.btn_mute.clicked.connect(self._toggle_mute)
        ctrl_layout.addWidget(self.btn_mute)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(100)
        self.slider_vol.setFixedWidth(75)
        self.slider_vol.setToolTip("Playback Volume")
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        ctrl_layout.addWidget(self.slider_vol)

        # Playback Speed Dropdown
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.combo_speed.setCurrentText("1.0x")
        self.combo_speed.setToolTip("Playback Speed")
        self.combo_speed.setFixedWidth(68)
        self.combo_speed.currentTextChanged.connect(self._on_speed_changed)
        ctrl_layout.addWidget(self.combo_speed)

        # Trimmer Controls Card
        trim_card = QFrame(self)
        trim_card.setStyleSheet("background-color: #161820; border-radius: 8px; padding: 2px;")
        trim_layout = QHBoxLayout(trim_card)
        trim_layout.setContentsMargins(8, 4, 8, 4)
        trim_layout.setSpacing(6)

        trim_layout.addWidget(QLabel("Trim Start:"))
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0.0, 9999.0)
        self.spin_start.setValue(0.0)
        self.spin_start.setSingleStep(0.5)
        self.spin_start.setSuffix("s")
        trim_layout.addWidget(self.spin_start)

        btn_set_start = QPushButton("📍")
        btn_set_start.setToolTip("Set Start to current playback position")
        btn_set_start.setFixedWidth(28)
        btn_set_start.clicked.connect(self._set_start_to_current)
        trim_layout.addWidget(btn_set_start)

        trim_layout.addWidget(QLabel("End:"))
        self.spin_end = QDoubleSpinBox()
        self.spin_end.setRange(0.0, 9999.0)
        self.spin_end.setValue(0.0)
        self.spin_end.setSingleStep(0.5)
        self.spin_end.setSuffix("s")
        trim_layout.addWidget(self.spin_end)

        btn_set_end = QPushButton("📍")
        btn_set_end.setToolTip("Set End to current playback position")
        btn_set_end.setFixedWidth(28)
        btn_set_end.clicked.connect(self._set_end_to_current)
        trim_layout.addWidget(btn_set_end)

        self.btn_trim = QPushButton("✂️ Trim")
        self.btn_trim.clicked.connect(self._trim_action)
        trim_layout.addWidget(self.btn_trim)

        ctrl_layout.addWidget(trim_card, 1)
        layout.addLayout(ctrl_layout)

        # 4. File Meta Info
        file_size_mb = os.path.getsize(self.video_path) / (1024 * 1024) if os.path.exists(self.video_path) else 0
        self.lbl_info = QLabel(f"File: {os.path.basename(self.video_path)} | Size: {file_size_mb:.2f} MB")
        self.lbl_info.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(self.lbl_info)

        # 5. Export & Actions Row
        actions_layout = QHBoxLayout()

        self.btn_copy = QPushButton("📋 Copy File")
        self.btn_copy.setToolTip("Copy video file directly to clipboard for Ctrl+V paste")
        self.btn_copy.clicked.connect(self._copy_video_file)
        actions_layout.addWidget(self.btn_copy)

        self.btn_snapshot = QPushButton("📸 Snapshot")
        self.btn_snapshot.setToolTip("Capture current frame as PNG image & copy to clipboard")
        self.btn_snapshot.clicked.connect(self._take_snapshot)
        actions_layout.addWidget(self.btn_snapshot)

        btn_gif = QPushButton("🎞️ Make GIF")
        btn_gif.clicked.connect(self._export_gif)
        actions_layout.addWidget(btn_gif)

        btn_audio = QPushButton("🎵 Extract MP3")
        btn_audio.clicked.connect(self._extract_audio)
        actions_layout.addWidget(btn_audio)

        btn_show = QPushButton("📂 Open Folder")
        btn_show.clicked.connect(lambda: post_processor.open_folder(os.path.dirname(self.video_path)))
        actions_layout.addWidget(btn_show)

        actions_layout.addStretch()

        btn_done = QPushButton("Close")
        btn_done.setStyleSheet("background-color: #6366F1; color: white; font-weight: bold; min-width: 90px;")
        btn_done.clicked.connect(self.close)
        actions_layout.addWidget(btn_done)

        layout.addLayout(actions_layout)

    def _connect_signals(self):
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _on_duration_changed(self, duration_ms: int):
        self.duration_ms = max(0, duration_ms)
        duration_sec = self.duration_ms / 1000.0
        self.spin_start.setRange(0.0, duration_sec)
        self.spin_end.setRange(0.0, duration_sec)
        self.spin_end.setValue(duration_sec)

        file_size_mb = os.path.getsize(self.video_path) / (1024 * 1024) if os.path.exists(self.video_path) else 0
        self.lbl_info.setText(f"File: {os.path.basename(self.video_path)} | Size: {file_size_mb:.2f} MB | Length: {duration_sec:.1f}s")
        self._update_time_label(self.player.position(), self.duration_ms)

    def _on_position_changed(self, pos_ms: int):
        if not self._slider_dragging and self.duration_ms > 0:
            val = int((pos_ms / self.duration_ms) * 1000)
            self.slider_timeline.blockSignals(True)
            self.slider_timeline.setValue(val)
            self.slider_timeline.blockSignals(False)
        self._update_time_label(pos_ms, self.duration_ms)

    def _update_time_label(self, pos_ms: int, dur_ms: int):
        cur_s = int(pos_ms // 1000)
        tot_s = int(dur_ms // 1000)
        self.lbl_time.setText(f"{cur_s // 60:02d}:{cur_s % 60:02d} / {tot_s // 60:02d}:{tot_s % 60:02d}")

    def _on_slider_pressed(self):
        self._slider_dragging = True

    def _on_slider_moved(self, val: int):
        if self.duration_ms > 0:
            target_ms = int((val / 1000.0) * self.duration_ms)
            self._update_time_label(target_ms, self.duration_ms)

    def _on_slider_released(self):
        self._slider_dragging = False
        if self.duration_ms > 0:
            target_ms = int((self.slider_timeline.value() / 1000.0) * self.duration_ms)
            self.player.setPosition(target_ms)

    def _toggle_playback(self):
        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            # If at or near the end, restart from beginning
            if self.duration_ms > 0 and self.player.position() >= self.duration_ms - 200:
                self.player.setPosition(0)
            self.player.play()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸ Pause")
        else:
            self.btn_play.setText("▶ Play")

    def _toggle_mute(self):
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        self.btn_mute.setText("🔇" if not is_muted else "🔊")

    def _on_volume_changed(self, val: int):
        vol = val / 100.0
        self.audio_output.setVolume(vol)
        if val == 0:
            self.btn_mute.setText("🔇")
        else:
            self.btn_mute.setText("🔊")
            if self.audio_output.isMuted():
                self.audio_output.setMuted(False)

    def _set_start_to_current(self):
        cur_sec = round(self.player.position() / 1000.0, 2)
        self.spin_start.setValue(cur_sec)

    def _set_end_to_current(self):
        cur_sec = round(self.player.position() / 1000.0, 2)
        self.spin_end.setValue(cur_sec)

    def _trim_action(self):
        start = self.spin_start.value()
        end = self.spin_end.value()
        if start >= end:
            QMessageBox.warning(self, "Invalid Range", "Start time must be less than end time.")
            return

        base, ext = os.path.splitext(self.video_path)
        out_path = f"{base}_trimmed{ext}"
        if post_processor.trim_video(self.video_path, out_path, start, end):
            QMessageBox.information(self, "Trim Success", f"Trimmed clip saved with audio to:\n{out_path}")
        else:
            QMessageBox.critical(self, "Trim Error", "Failed to trim video.")

    def _export_gif(self):
        base, _ = os.path.splitext(self.video_path)
        gif_path = f"{base}.gif"
        if post_processor.convert_to_gif(self.video_path, gif_path):
            QMessageBox.information(self, "GIF Created", f"Animated GIF saved to:\n{gif_path}")
        else:
            QMessageBox.critical(self, "Export Error", "Failed to create animated GIF.")

    def _extract_audio(self):
        base, _ = os.path.splitext(self.video_path)
        audio_path = f"{base}.mp3"
        if post_processor.extract_audio(self.video_path, audio_path):
            QMessageBox.information(self, "Audio Extracted", f"MP3 audio saved to:\n{audio_path}")
        else:
            QMessageBox.critical(self, "Export Error", "Failed to extract MP3 audio.")

    def _on_speed_changed(self, text: str):
        try:
            rate = float(text.replace("x", ""))
            self.player.setPlaybackRate(rate)
        except Exception:
            pass

    def _copy_video_file(self):
        """Copy video file URL and path to clipboard for Ctrl+V paste."""
        if not os.path.exists(self.video_path):
            return
        abs_path = os.path.abspath(self.video_path)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(abs_path)])
        mime.setText(abs_path)
        QApplication.clipboard().setMimeData(mime)

        orig_text = self.btn_copy.text()
        self.btn_copy.setText("✔ Copied!")
        QTimer.singleShot(1800, lambda: self.btn_copy.setText(orig_text))

    def _take_snapshot(self):
        """Extract lossless PNG frame at current playback position and copy to clipboard."""
        if not os.path.exists(self.video_path):
            return
        pos_sec = max(0.0, self.player.position() / 1000.0)
        from src.core.hardware_detect import get_ffmpeg_binary
        import subprocess

        ffmpeg_bin = get_ffmpeg_binary()
        dir_name = os.path.dirname(self.video_path)
        base_name = os.path.splitext(os.path.basename(self.video_path))[0]
        out_png = os.path.join(dir_name, f"{base_name}_Snapshot_{int(pos_sec * 1000)}ms.png")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(pos_sec),
            "-i", self.video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_png,
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags, timeout=5)
            if os.path.exists(out_png):
                img = QImage(out_png)
                if not img.isNull():
                    QApplication.clipboard().setImage(img)
                orig_text = self.btn_snapshot.text()
                self.btn_snapshot.setText("✔ Saved!")
                QTimer.singleShot(1800, lambda: self.btn_snapshot.setText(orig_text))
        except Exception as e:
            QMessageBox.warning(self, "Snapshot Error", f"Failed to capture frame: {e}")

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
