"""
FFmpeg subprocess writer for real-time video encoding and audio muxing.
Supports 4K Ultra HD resolution scaling (Lanczos/Bicubic), high-bitrate profiles,
and hardware GPU acceleration with automatic CPU fallback.
"""

import subprocess
import os
import time
from typing import Optional, Dict, Any, Tuple
from src.core.hardware_detect import get_ffmpeg_binary, hardware_detector
from src.config.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    QUALITY_PROFILES,
    RESOLUTION_PRESETS,
    DEFAULT_QUALITY,
    DEFAULT_RESOLUTION,
    FORMAT_MP4,
)


class FFmpegWriter:
    """Manages an FFmpeg subprocess that consumes raw video frames from stdin."""

    def __init__(
        self,
        output_filepath: str,
        width: int,
        height: int,
        fps: int = 60,
        codec: str = "auto",
        quality_profile: str = DEFAULT_QUALITY,
        has_audio: bool = False,
        temp_audio_file: Optional[str] = None,
        target_resolution: Optional[str] = DEFAULT_RESOLUTION,
    ):
        self.output_filepath = output_filepath
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.quality_profile = quality_profile
        self.has_audio = has_audio
        self.temp_audio_file = temp_audio_file
        self.target_resolution = target_resolution

        self.ffmpeg_path = get_ffmpeg_binary()
        self.process: Optional[subprocess.Popen] = None
        self._is_open = False
        self.intermediate_video: Optional[str] = None

    def _resolve_target_dimensions(self) -> Tuple[int, int]:
        """Resolve output scaling dimensions."""
        if not self.target_resolution or self.target_resolution == "Native Display (Original)":
            return (self.width, self.height)

        preset = RESOLUTION_PRESETS.get(self.target_resolution)
        if preset and isinstance(preset, (tuple, list)):
            target_w, target_h = preset
            # Guard against distorting aspect ratios (e.g. vertical 9:16 reel captured with 16:9 preset)
            src_ar = self.width / max(1, self.height)
            tgt_ar = target_w / max(1, target_h)
            if abs(src_ar - tgt_ar) > 0.05:
                return (self.width, self.height)
            return (target_w, target_h)

        return (self.width, self.height)

    def _resolve_codec(self, target_w: int, target_h: int) -> str:
        """Resolve auto codec to best working hardware encoder or CPU fallback."""
        if target_w > 1920 or target_h > 1080:
            # NVENC supports 4K/8K natively on Nvidia.
            # On AMD/Intel without verified 4K profile, use multithreaded libx264 for flawless 4K output.
            best = hardware_detector.get_best_h264_encoder()
            if "nvenc" in best:
                return best
            return "libx264"

        if self.codec == "auto" or not self.codec:
            return hardware_detector.get_best_h264_encoder()
        return self.codec

    def open(self) -> bool:
        """Start the FFmpeg encoding subprocess."""
        target_w, target_h = self._resolve_target_dimensions()
        selected_codec = self._resolve_codec(target_w, target_h)
        profile_settings = QUALITY_PROFILES.get(
            self.quality_profile, QUALITY_PROFILES.get(DEFAULT_QUALITY, {"video_bitrate": "60M", "crf": 14, "preset": "fast"})
        )

        target_video_out = self.output_filepath
        if self.has_audio and self.temp_audio_file:
            target_video_out = self.output_filepath + ".temp_vid.mp4"
        self.intermediate_video = target_video_out

        def build_cmd(codec_name: str) -> list:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-pix_fmt", "bgra",
                "-s", f"{self.width}x{self.height}",
                "-r", str(self.fps),
                "-i", "-",
            ]

            # High Quality 4K Scale filter if scaling is needed
            if target_w != self.width or target_h != self.height:
                cmd.extend(["-vf", f"scale={target_w}:{target_h}:flags=lanczos"])

            cmd.extend(["-c:v", codec_name])

            if "nvenc" in codec_name:
                cmd.extend(["-preset", "p4", "-rc", "vbr", "-cq", str(profile_settings["crf"]), "-b:v", profile_settings["video_bitrate"]])
            elif "qsv" in codec_name:
                cmd.extend(["-preset", "medium", "-global_quality", str(profile_settings["crf"])])
            elif "amf" in codec_name:
                cmd.extend(["-quality", "quality", "-b:v", profile_settings["video_bitrate"]])
            else:
                # High-performance multithreaded libx264
                cmd.extend(["-preset", "ultrafast", "-crf", str(profile_settings["crf"]), "-tune", "zerolatency", "-threads", "0"])

            cmd.extend(["-pix_fmt", "yuv420p"])

            if target_video_out.lower().endswith(".mp4"):
                cmd.extend(["-movflags", "+faststart"])

            cmd.append(target_video_out)
            return cmd

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        # Try launching with primary codec
        cmd = build_cmd(selected_codec)
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                bufsize=10**7,
            )
            time.sleep(0.04)
            if self.process.poll() is None:
                self._is_open = True
                return True
            else:
                print(f"[FFmpegWriter] Codec {selected_codec} exited immediately, falling back to libx264")
        except Exception as e:
            print(f"[FFmpegWriter] Error with {selected_codec}: {e}, falling back to libx264")

        # Fallback to CPU libx264
        cmd = build_cmd("libx264")
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                bufsize=10**7,
            )
            time.sleep(0.03)
            if self.process.poll() is None:
                self._is_open = True
                return True
            else:
                print(f"[FFmpegWriter] Fallback libx264 exited with code {self.process.poll()}")
                self._is_open = False
                return False
        except Exception as e2:
            print(f"[FFmpegWriter] Fallback to libx264 failed: {e2}")
            self._is_open = False
            return False

    def write_frame(self, frame_bytes: bytes) -> bool:
        """Send a raw BGR24 frame to FFmpeg stdin."""
        if not self._is_open or not self.process or not self.process.stdin:
            return False
        try:
            self.process.stdin.write(frame_bytes)
            return True
        except (BrokenPipeError, OSError):
            self._is_open = False
            return False

    def close(self) -> bool:
        """Flush stdin and cleanly terminate the FFmpeg process."""
        if not self.process:
            return False

        self._is_open = False
        try:
            if self.process.stdin:
                try:
                    self.process.stdin.flush()
                except Exception:
                    pass
                try:
                    self.process.stdin.close()
                except Exception:
                    pass
            self.process.wait(timeout=10)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        finally:
            self.process = None

        # If audio was recorded separately, perform instantaneous remux
        if (
            self.has_audio
            and self.temp_audio_file
            and os.path.exists(self.temp_audio_file)
            and self.intermediate_video
            and os.path.exists(self.intermediate_video)
        ):
            self._mux_audio_video()

        return True

    def _mux_audio_video(self):
        """Instantaneously remux video and audio into final output file with faststart."""
        # 1. Guard against empty audio file (standard WAV header is 44 bytes)
        audio_size = os.path.getsize(self.temp_audio_file) if (self.temp_audio_file and os.path.exists(self.temp_audio_file)) else 0
        if audio_size <= 44:
            print("[FFmpegWriter] Temp audio file contains 0 audio frames. Preserving pristine video without audio.")
            if os.path.exists(self.intermediate_video) and self.intermediate_video != self.output_filepath:
                try:
                    if os.path.exists(self.output_filepath):
                        os.remove(self.output_filepath)
                    os.rename(self.intermediate_video, self.output_filepath)
                except Exception as e:
                    print(f"[FFmpegWriter] Error promoting intermediate video: {e}")
            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                try:
                    os.remove(self.temp_audio_file)
                except Exception:
                    pass
            return

        try:
            # 2. Remux video + audio with A/V sync filter (do NOT use -shortest to avoid truncating video)
            remux_cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", self.intermediate_video,
                "-i", self.temp_audio_file,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
                "-movflags", "+faststart",
                self.output_filepath,
            ]
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.run(
                remux_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                check=True,
            )

            # 3. Verify output integrity
            if os.path.exists(self.output_filepath) and os.path.getsize(self.output_filepath) > 1000:
                # Cleanup temp files only on verified success
                if os.path.exists(self.intermediate_video) and self.intermediate_video != self.output_filepath:
                    try:
                        os.remove(self.intermediate_video)
                    except Exception:
                        pass
                if os.path.exists(self.temp_audio_file):
                    try:
                        os.remove(self.temp_audio_file)
                    except Exception:
                        pass
            else:
                # If remux output was unexpectedly small or missing, fall back to intermediate video
                print("[FFmpegWriter] Remuxed output was unexpectedly small. Falling back to video.")
                if os.path.exists(self.intermediate_video) and self.intermediate_video != self.output_filepath:
                    if os.path.exists(self.output_filepath):
                        os.remove(self.output_filepath)
                    os.rename(self.intermediate_video, self.output_filepath)

        except Exception as e:
            print(f"[FFmpegWriter] Remux error: {e}")
            if os.path.exists(self.intermediate_video) and self.intermediate_video != self.output_filepath:
                try:
                    if os.path.exists(self.output_filepath):
                        os.remove(self.output_filepath)
                    os.rename(self.intermediate_video, self.output_filepath)
                except Exception:
                    pass
