"""
Recording controller orchestrating video, audio, and muxer workers.
"""

import os
import time
import queue
import wave
import threading
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from src.config.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_FPS,
    FORMAT_MP4,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
)
from src.config.settings_manager import settings
from src.core.video_capture import VideoCaptureWorker
from src.core.audio_capture import AudioCaptureWorker
from src.core.ffmpeg_writer import FFmpegWriter


class RecordingController(QObject):
    """Main orchestrator for recording lifecycle."""

    # Qt Signals for UI updates
    state_changed = pyqtSignal(str)          # "idle", "countdown", "recording", "paused", "finalizing"
    time_updated = pyqtSignal(int)            # Elapsed seconds
    fps_updated = pyqtSignal(float)          # Actual FPS
    audio_levels_updated = pyqtSignal(float, float) # (system_level, mic_level 0.0-1.0)
    recording_finished = pyqtSignal(str)      # Output filepath
    error_occurred = pyqtSignal(str)         # Error message

    def __init__(self):
        super().__init__()
        self.state = "idle"
        self.video_worker: Optional[VideoCaptureWorker] = None
        self.audio_worker: Optional[AudioCaptureWorker] = None
        self.ffmpeg_writer: Optional[FFmpegWriter] = None

        self.video_queue: queue.Queue = queue.Queue(maxsize=120)
        self.audio_queue: queue.Queue = queue.Queue(maxsize=200)

        self.overlay_callback: Optional[Callable] = None

        self._start_time = 0.0
        self._elapsed_offset = 0.0
        self._pause_start = 0.0
        self._is_recording = False
        self._is_paused = False

        self._timer_thread: Optional[threading.Thread] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._audio_writer_thread: Optional[threading.Thread] = None

        self.current_output_file: Optional[str] = None
        self.temp_audio_file: Optional[str] = None

    def set_overlay_callback(self, callback: Callable):
        """Set a frame post-processor for annotations, webcam, cursor ripples."""
        self.overlay_callback = callback

    def _generate_output_path(self, ext: str = FORMAT_MP4) -> str:
        """Generate a timestamped filename in output directory."""
        output_dir = settings.get("output_dir", DEFAULT_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Record_{timestamp}.{ext}"
        return os.path.join(output_dir, filename)

    def start_recording(self, region: Optional[Dict[str, int]] = None) -> bool:
        """Initialize and start capture workers."""
        if self.state != "idle":
            return False

        self._is_recording = True
        self._is_paused = False
        self._elapsed_offset = 0.0

        # Output paths
        ext = settings.get("format", FORMAT_MP4)
        self.current_output_file = self._generate_output_path(ext)
        temp_dir = os.path.join(settings.get("output_dir", DEFAULT_OUTPUT_DIR), ".temp")
        os.makedirs(temp_dir, exist_ok=True)
        self.temp_audio_file = os.path.join(temp_dir, f"temp_audio_{int(time.time())}.wav")

        fps = int(settings.get("fps", DEFAULT_FPS))
        codec = settings.get("encoder", "auto")
        quality = settings.get("quality_profile", "High (10 Mbps)")

        # Initialize Video Capture Worker
        self.video_queue = queue.Queue(maxsize=120)
        self.video_worker = VideoCaptureWorker(
            frame_queue=self.video_queue,
            region=region,
            target_fps=fps,
            show_cursor=settings.get("show_cursor", True),
            overlay_callback=self.overlay_callback,
        )

        # Initialize Audio Capture Worker
        rec_sys = settings.get("record_system_audio", True)
        rec_mic = settings.get("record_microphone", False)
        has_audio = rec_sys or rec_mic

        if has_audio:
            self.audio_queue = queue.Queue(maxsize=200)
            self.audio_worker = AudioCaptureWorker(
                audio_queue=self.audio_queue,
                record_system_audio=rec_sys,
                record_mic=rec_mic,
                mic_device_id=settings.get("mic_device_id"),
                system_volume=settings.get("system_audio_volume", 100) / 100.0,
                mic_volume=settings.get("mic_volume", 100) / 100.0,
                level_callback=lambda sys_lvl, mic_lvl: self.audio_levels_updated.emit(sys_lvl, mic_lvl),
            )
            # Start background audio writer to write WAV temp file
            self._audio_writer_thread = threading.Thread(
                target=self._audio_file_writer_loop, daemon=True, name="AudioFileWriter"
            )
            self._audio_writer_thread.start()
            self.audio_worker.start()

        # Initialize FFmpeg Writer
        self.ffmpeg_writer = FFmpegWriter(
            output_filepath=self.current_output_file,
            width=self.video_worker.width,
            height=self.video_worker.height,
            fps=fps,
            codec=codec,
            quality_profile=quality,
            has_audio=has_audio,
            temp_audio_file=self.temp_audio_file if has_audio else None,
        )

        if not self.ffmpeg_writer.open():
            self.error_occurred.emit("Failed to initialize video encoder.")
            self._cleanup()
            return False

        # Start Video Capture Worker
        self.video_worker.start()

        # Start Video Frame Consumer Thread
        self._writer_thread = threading.Thread(
            target=self._video_writer_loop, daemon=True, name="VideoFrameWriter"
        )
        self._writer_thread.start()

        # Start Timer Thread
        self._start_time = time.perf_counter()
        self._timer_thread = threading.Thread(
            target=self._timer_loop, daemon=True, name="RecordingTimer"
        )
        self._timer_thread.start()

        self.state = "recording"
        self.state_changed.emit(self.state)
        return True

    def _video_writer_loop(self):
        """Pulls video frames from queue and feeds FFmpeg stdin."""
        while self._is_recording or not self.video_queue.empty():
            try:
                frame_data = self.video_queue.get(timeout=0.05)
                frame, pts = frame_data
                if self.ffmpeg_writer:
                    self.ffmpeg_writer.write_frame(frame.tobytes())
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[RecordingController] Video write error: {e}")

    def _audio_file_writer_loop(self):
        """Consumes PCM audio chunks and streams into temporary WAV file."""
        if not self.temp_audio_file:
            return

        wav_file = wave.open(self.temp_audio_file, "wb")
        wav_file.setnchannels(AUDIO_CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(AUDIO_SAMPLE_RATE)

        try:
            while self._is_recording or not self.audio_queue.empty():
                try:
                    pcm_bytes = self.audio_queue.get(timeout=0.05)
                    wav_file.writeframes(pcm_bytes)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[RecordingController] Audio file write error: {e}")
        finally:
            wav_file.close()

    def _timer_loop(self):
        """Updates elapsed time and actual capture FPS."""
        while self._is_recording:
            if not self._is_paused:
                elapsed = int(time.perf_counter() - self._start_time - self._elapsed_offset)
                self.time_updated.emit(max(0, elapsed))
                if self.video_worker:
                    self.fps_updated.emit(self.video_worker.actual_fps)
            time.sleep(0.5)

    def pause_recording(self):
        """Pause recording."""
        if self.state == "recording":
            self._is_paused = True
            self._pause_start = time.perf_counter()
            if self.video_worker:
                self.video_worker.pause()
            if self.audio_worker:
                self.audio_worker.pause()
            self.state = "paused"
            self.state_changed.emit(self.state)

    def resume_recording(self):
        """Resume recording."""
        if self.state == "paused":
            pause_duration = time.perf_counter() - self._pause_start
            self._elapsed_offset += pause_duration
            self._is_paused = False
            if self.video_worker:
                self.video_worker.resume()
            if self.audio_worker:
                self.audio_worker.resume()
            self.state = "recording"
            self.state_changed.emit(self.state)

    def stop_recording(self):
        """Stop capture, drain queues, close FFmpeg, and finalize file."""
        if self.state not in ["recording", "paused"]:
            return

        self.state = "finalizing"
        self.state_changed.emit(self.state)
        self._is_recording = False
        self._is_paused = False

        # Stop workers
        if self.video_worker:
            self.video_worker.stop()
            self.video_worker.join(timeout=2.0)

        if self.audio_worker:
            self.audio_worker.stop()

        # Wait for frame queues to drain into FFmpeg
        if self._writer_thread:
            self._writer_thread.join(timeout=3.0)

        if self._audio_writer_thread:
            self._audio_writer_thread.join(timeout=3.0)

        # Close FFmpeg & Remux
        if self.ffmpeg_writer:
            self.ffmpeg_writer.close()

        output_path = self.current_output_file
        self._cleanup()

        self.state = "idle"
        self.state_changed.emit(self.state)
        if output_path and os.path.exists(output_path):
            self.recording_finished.emit(output_path)

    def _cleanup(self):
        self.video_worker = None
        self.audio_worker = None
        self.ffmpeg_writer = None


# Global controller instance
controller = RecordingController()
