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
    DEFAULT_QUALITY,
    DEFAULT_RESOLUTION,
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
        self._start_time: float = 0.0
        self._stop_time: Optional[float] = None
        self._elapsed_offset: float = 0.0

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
        quality = settings.get("quality_profile", DEFAULT_QUALITY)
        resolution = settings.get("resolution", DEFAULT_RESOLUTION)

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
        rec_webcam_audio = settings.get("record_webcam_audio", False)

        webcam_audio_id = settings.get("webcam_audio_device_id")
        if rec_webcam_audio and webcam_audio_id is None:
            active_cam_name = settings.get("webcam_device_name", "")
            webcam_audio_id = AudioCaptureWorker.match_webcam_audio(active_cam_name)

        has_audio = rec_sys or rec_mic or (rec_webcam_audio and webcam_audio_id is not None)

        # Initialize FFmpeg Writer FIRST so the encoder process is spun up and ready
        self.ffmpeg_writer = FFmpegWriter(
            output_filepath=self.current_output_file,
            width=self.video_worker.width,
            height=self.video_worker.height,
            fps=fps,
            codec=codec,
            quality_profile=quality,
            has_audio=has_audio,
            temp_audio_file=self.temp_audio_file if has_audio else None,
            target_resolution=resolution if region is None else None,
        )

        if not self.ffmpeg_writer.open():
            self.error_occurred.emit("Failed to initialize video encoder.")
            self._cleanup()
            return False

        # Unified start timestamp
        self._start_time = time.perf_counter()
        self._stop_time = None
        self._elapsed_offset = 0.0

        if has_audio:
            self.audio_queue = queue.Queue(maxsize=300)
            self.audio_worker = AudioCaptureWorker(
                audio_queue=self.audio_queue,
                record_system_audio=rec_sys,
                record_mic=rec_mic,
                mic_device_id=settings.get("mic_device_id"),
                record_webcam_audio=rec_webcam_audio and (webcam_audio_id is not None),
                webcam_audio_device_id=webcam_audio_id,
                system_volume=settings.get("system_audio_volume", 100) / 100.0,
                mic_volume=settings.get("mic_volume", 100) / 100.0,
                webcam_volume=settings.get("webcam_audio_volume", 100) / 100.0,
                noise_reduction=settings.get("noise_reduction", 0) / 100.0,
                level_callback=lambda sys_lvl, mic_lvl: self.audio_levels_updated.emit(sys_lvl, mic_lvl),
            )
            # Start background audio writer to write WAV temp file
            self._audio_writer_thread = threading.Thread(
                target=self._audio_file_writer_loop, daemon=True, name="AudioFileWriter"
            )
            self._audio_writer_thread.start()
            self.audio_worker.start()
            self.audio_worker.start_recording(self._start_time)

        # Start Video Capture Worker with synchronized start time
        self.video_worker.start_recording(self._start_time)

        # Start Video Frame Consumer Thread with CFR pacing
        self._writer_thread = threading.Thread(
            target=self._video_writer_loop, daemon=True, name="VideoFrameWriter"
        )
        self._writer_thread.start()

        # Start Timer Thread
        self._timer_thread = threading.Thread(
            target=self._timer_loop, daemon=True, name="RecordingTimer"
        )
        self._timer_thread.start()

        self.state = "recording"
        self.state_changed.emit(self.state)
        return True

    def _video_writer_loop(self):
        """
        Pulls video frames from queue and feeds FFmpeg stdin with strict CFR (Constant Frame Rate)
        timestamp pacing. Ensures video playback duration precisely matches audio recording duration.
        """
        target_fps = self.video_worker.target_fps
        t0 = self._start_time
        frames_written = 0
        last_frame_bytes = None

        while self._is_recording or not self.video_queue.empty():
            if self._is_paused:
                time.sleep(0.02)
                continue

            # 1. Pull next captured frame from queue
            try:
                frame_data = self.video_queue.get(timeout=0.02)
                frame, pts = frame_data
                last_frame_bytes = frame.tobytes()
                if not self.ffmpeg_writer.write_frame(last_frame_bytes):
                    return
                frames_written += 1
            except queue.Empty:
                pass

            if last_frame_bytes is None:
                continue

            # 2. Check if we need to emit duplicate frames to keep pace with real elapsed time
            now = time.perf_counter()
            elapsed = max(0.0, now - t0 - self._elapsed_offset)
            expected_frames = int(elapsed * target_fps)

            if frames_written < expected_frames:
                # Catch up by duplicating last valid frame to maintain strict CFR alignment
                needed = min(expected_frames - frames_written, 10)
                for _ in range(needed):
                    if not self.ffmpeg_writer.write_frame(last_frame_bytes):
                        return
                    frames_written += 1

            time.sleep(0.001)

        # Pad frames up to exact final stop time if needed
        if last_frame_bytes and self._stop_time and self._stop_time > t0:
            final_elapsed = max(0.0, self._stop_time - t0 - self._elapsed_offset)
            final_expected = int(final_elapsed * target_fps)
            while frames_written < final_expected:
                if not self.ffmpeg_writer.write_frame(last_frame_bytes):
                    break
                frames_written += 1

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

    def set_noise_reduction(self, level: int):
        """Update noise reduction level in real-time (0 to 100)."""
        if self.audio_worker:
            self.audio_worker.set_noise_reduction(level / 100.0)

    def stop_recording(self):
        """Stop capture, drain queues, close FFmpeg, and finalize file."""
        if self.state not in ["recording", "paused"]:
            return

        self.state = "finalizing"
        self.state_changed.emit(self.state)
        self._is_recording = False
        self._is_paused = False
        self._stop_time = time.perf_counter()

        # Stop audio and video capture simultaneously
        if self.audio_worker:
            self.audio_worker.stop_recording()
            self.audio_worker.stop()

        if self.video_worker:
            self.video_worker.stop()

        # Wait for frame queues to drain into FFmpeg
        if self._writer_thread:
            self._writer_thread.join(timeout=3.0)

        if self._audio_writer_thread:
            self._audio_writer_thread.join(timeout=3.0)

        # Close FFmpeg & Remux with A/V sync
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
