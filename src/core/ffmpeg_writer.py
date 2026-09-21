"""
FFmpeg subprocess writer for real-time video encoding and audio muxing.
"""

import subprocess
import os
import time
from typing import Optional, Dict, Any
from src.core.hardware_detect import get_ffmpeg_binary, hardware_detector
from src.config.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    QUALITY_PROFILES,
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
        quality_profile: str = "High (10 Mbps)",
        has_audio: bool = False,
        temp_audio_file: Optional[str] = None,
    ):
        self.output_filepath = output_filepath
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.quality_profile = quality_profile
        self.has_audio = has_audio
        self.temp_audio_file = temp_audio_file

        self.ffmpeg_path = get_ffmpeg_binary()
        self.process: Optional[subprocess.Popen] = None
        self._is_open = False
        self.intermediate_video: Optional[str] = None

    def _resolve_codec(self) -> str:
        """Resolve auto codec to best working hardware encoder or CPU fallback."""
        if self.codec == "auto" or not self.codec:
            return hardware_detector.get_best_h264_encoder()
        return self.codec

    def open(self) -> bool:
        """Start the FFmpeg encoding subprocess."""
        selected_codec = self._resolve_codec()
        profile_settings = QUALITY_PROFILES.get(
            self.quality_profile, QUALITY_PROFILES["High (10 Mbps)"]
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
                "-pix_fmt", "bgr24",
                "-s", f"{self.width}x{self.height}",
                "-r", str(self.fps),
                "-i", "-",
                "-c:v", codec_name,
            ]
            if "nvenc" in codec_name:
                cmd.extend(["-preset", "p4", "-rc", "vbr", "-cq", str(profile_settings["crf"]), "-b:v", profile_settings["video_bitrate"]])
            elif "qsv" in codec_name:
                cmd.extend(["-preset", "medium", "-global_quality", str(profile_settings["crf"])])
            elif "amf" in codec_name:
                cmd.extend(["-quality", "balanced", "-b:v", profile_settings["video_bitrate"]])
            else:
                cmd.extend(["-preset", "ultrafast", "-crf", str(profile_settings["crf"]), "-tune", "zerolatency"])

            cmd.extend(["-pix_fmt", "yuv420p"])

            if target_video_out.lower().endswith(".mp4"):
                cmd.extend(["-movflags", "+faststart"])

            cmd.append(target_video_out)
            return cmd

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        # Try with selected codec
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
            self._is_open = True
            return True
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
                self._is_open = True
                return True
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
            self.process.wait(timeout=5)
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
        try:
            remux_cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", self.intermediate_video,
                "-i", self.temp_audio_file,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
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
            # Cleanup temp files
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
        except Exception as e:
            print(f"[FFmpegWriter] Remux error: {e}")
            if os.path.exists(self.intermediate_video) and self.intermediate_video != self.output_filepath:
                try:
                    if os.path.exists(self.output_filepath):
                        os.remove(self.output_filepath)
                    os.rename(self.intermediate_video, self.output_filepath)
                except Exception:
                    pass
