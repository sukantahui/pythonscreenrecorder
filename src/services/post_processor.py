"""
Post-recording video processing, trimming, and GIF conversion utilities.
"""

import subprocess
import os
import sys
from typing import Optional, Callable
from src.core.hardware_detect import get_ffmpeg_binary


class PostProcessor:
    """Provides video editing and export capabilities."""

    def __init__(self):
        self.ffmpeg_path = get_ffmpeg_binary()

    def trim_video(
        self,
        input_path: str,
        output_path: str,
        start_sec: float,
        end_sec: float,
    ) -> bool:
        """Trim video segment without re-encoding."""
        duration = max(0.1, end_sec - start_sec)
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_sec),
            "-i", input_path,
            "-t", str(duration),
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                check=True,
            )
            return True
        except Exception as e:
            print(f"[PostProcessor] Trim error: {e}")
            return False

    def convert_to_gif(
        self,
        input_path: str,
        output_path: str,
        fps: int = 15,
        width: int = 720,
    ) -> bool:
        """Convert video clip to high-quality animated GIF with palettegen."""
        vf_filter = f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vf", vf_filter,
            output_path,
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                check=True,
            )
            return True
        except Exception as e:
            print(f"[PostProcessor] GIF conversion error: {e}")
            return False

    def extract_audio(self, input_path: str, output_path: str) -> bool:
        """Extract audio stream to MP3 file."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                check=True,
            )
            return True
        except Exception as e:
            print(f"[PostProcessor] Audio extraction error: {e}")
            return False

    @staticmethod
    def open_folder(folder_path: str):
        """Open system file explorer to folder."""
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])


post_processor = PostProcessor()
