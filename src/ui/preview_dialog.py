"""
Post-recording video player, trimmer, and export manager dialog.
"""

import os
import cv2
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap
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
    QFileDialog,
)
from src.services.post_processor import post_processor


class PreviewDialog(QDialog):
    """Instant playback, trimmer, and format exporter for recorded clips."""

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setWindowTitle(f"Recording Complete - {os.path.basename(video_path)}")
        self.setFixedSize(740, 560)
        self.setModal(True)

        self.cap = cv2.VideoCapture(self.video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0.0
        self.current_frame = 0
        self.is_playing = False

        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._next_frame)

        self._setup_ui()
        self._show_frame(0)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Video Preview Canvas
        self.lbl_video = QLabel(self)
        self.lbl_video.setStyleSheet("background-color: #000000; border-radius: 8px;")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setMinimumHeight(320)
        layout.addWidget(self.lbl_video)

        # Timeline Scrubber Bar
        scrub_layout = QHBoxLayout()
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        scrub_layout.addWidget(self.lbl_time)

        self.slider_timeline = QSlider(Qt.Orientation.Horizontal)
        self.slider_timeline.setRange(0, max(0, self.total_frames - 1))
        self.slider_timeline.valueChanged.connect(self._on_seek)
        scrub_layout.addWidget(self.slider_timeline)
        layout.addLayout(scrub_layout)

        # Playback Controls
        ctrl_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self.btn_play)

        # Trimmer Controls Card
        trim_card = QFrame(self)
        trim_card.setStyleSheet("background-color: #161820; border-radius: 8px; padding: 4px;")
        trim_layout = QHBoxLayout(trim_card)
        trim_layout.setContentsMargins(8, 4, 8, 4)

        trim_layout.addWidget(QLabel("Trim Start (s):"))
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0.0, max(0.0, self.duration_sec))
        self.spin_start.setValue(0.0)
        trim_layout.addWidget(self.spin_start)

        trim_layout.addWidget(QLabel("End (s):"))
        self.spin_end = QDoubleSpinBox()
        self.spin_end.setRange(0.0, max(0.0, self.duration_sec))
        self.spin_end.setValue(self.duration_sec)
        trim_layout.addWidget(self.spin_end)

        self.btn_trim = QPushButton("✂️ Trim")
        self.btn_trim.clicked.connect(self._trim_action)
        trim_layout.addWidget(self.btn_trim)

        ctrl_layout.addWidget(trim_card)
        layout.addLayout(ctrl_layout)

        # File Meta Info
        file_size_mb = os.path.getsize(self.video_path) / (1024 * 1024) if os.path.exists(self.video_path) else 0
        lbl_info = QLabel(f"File: {os.path.basename(self.video_path)} | Size: {file_size_mb:.2f} MB | Length: {self.duration_sec:.1f}s")
        lbl_info.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(lbl_info)

        # Export & Actions Row
        actions_layout = QHBoxLayout()
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
        btn_done.setStyleSheet("background-color: #6366F1; color: white;")
        btn_done.clicked.connect(self.close)
        actions_layout.addWidget(btn_done)

        layout.addLayout(actions_layout)

    def _show_frame(self, frame_idx: int):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                self.lbl_video.width(),
                self.lbl_video.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_video.setPixmap(pixmap)

            cur_sec = frame_idx / self.fps if self.fps > 0 else 0
            self.lbl_time.setText(f"{int(cur_sec // 60):02d}:{int(cur_sec % 60):02d} / {int(self.duration_sec // 60):02d}:{int(self.duration_sec % 60):02d}")

    def _on_seek(self, val: int):
        if not self.is_playing:
            self.current_frame = val
            self._show_frame(val)

    def _next_frame(self):
        self.current_frame += 1
        if self.current_frame >= self.total_frames:
            self.current_frame = 0
            self._toggle_playback()
            return
        self.slider_timeline.setValue(self.current_frame)
        self._show_frame(self.current_frame)

    def _toggle_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_timer.stop()
            self.btn_play.setText("▶ Play")
        else:
            self.is_playing = True
            interval = int(1000 / self.fps) if self.fps > 0 else 33
            self.play_timer.start(interval)
            self.btn_play.setText("⏸ Pause")

    def _trim_action(self):
        start = self.spin_start.value()
        end = self.spin_end.value()
        if start >= end:
            QMessageBox.warning(self, "Invalid Range", "Start time must be less than end time.")
            return

        base, ext = os.path.splitext(self.video_path)
        out_path = f"{base}_trimmed{ext}"
        if post_processor.trim_video(self.video_path, out_path, start, end):
            QMessageBox.information(self, "Trim Success", f"Trimmed clip saved to:\n{out_path}")
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

    def closeEvent(self, event):
        self.play_timer.stop()
        if self.cap:
            self.cap.release()
        super().closeEvent(event)
