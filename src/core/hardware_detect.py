"""
Hardware acceleration detector for FFmpeg encoders with live device validation.
"""

import subprocess
import shutil
from typing import List, Optional
import os


def get_ffmpeg_binary() -> str:
    """Find the best available FFmpeg executable path."""
    # 1. Try imageio_ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    # 2. Try system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # Fallback to plain name
    return "ffmpeg"


class HardwareDetector:
    """Probes and validates supported video encoders on active hardware."""

    def __init__(self):
        self.ffmpeg_path = get_ffmpeg_binary()
        self._working_encoders: Optional[List[str]] = None
        self._best_h264: Optional[str] = None

    def _test_encoder(self, encoder_name: str) -> bool:
        """Run a 1-frame dry run to verify GPU driver/hardware supports the encoder."""
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            res = subprocess.run(
                [
                    self.ffmpeg_path,
                    "-y",
                    "-f", "lavfi",
                    "-i", "color=c=black:s=64x64:d=0.05",
                    "-c:v", encoder_name,
                    "-f", "null",
                    "-",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                timeout=1,
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_available_encoders(self) -> List[str]:
        """Query and validate all hardware/software encoders that work on this machine."""
        if self._working_encoders is not None:
            return self._working_encoders

        candidates = [
            "h264_nvenc",
            "h264_amf",
            "h264_qsv",
            "libx264",
            "hevc_nvenc",
            "hevc_amf",
            "hevc_qsv",
            "libx265",
        ]

        working = []
        for candidate in candidates:
            if self._test_encoder(candidate):
                working.append(candidate)

        # Ensure at least libx264 is present
        if "libx264" not in working:
            working.append("libx264")

        self._working_encoders = working
        return working

    def get_best_h264_encoder(self) -> str:
        """Select highest performance hardware encoder available, or fallback to CPU."""
        if self._best_h264 is not None:
            return self._best_h264

        # Fast priority check: NVIDIA -> AMD -> Intel
        for candidate in ("h264_nvenc", "h264_amf", "h264_qsv"):
            if self._test_encoder(candidate):
                self._best_h264 = candidate
                return candidate

        self._best_h264 = "libx264"
        return "libx264"


hardware_detector = HardwareDetector()

# Pre-probe hardware encoders in background thread on startup
import threading
threading.Thread(target=hardware_detector.get_best_h264_encoder, daemon=True, name="HWEncoderProbe").start()

