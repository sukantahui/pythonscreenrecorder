"""
Integration tests for the screen recorder capture, 4K UHD scaling, and muxing engine.
"""

import sys
import os
import time
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.hardware_detect import hardware_detector, get_ffmpeg_binary
from src.core.controller import controller
from src.config.settings_manager import settings
from src.config.constants import DEFAULT_QUALITY, DEFAULT_RESOLUTION


class TestScreenRecorderEngine(unittest.TestCase):
    """Test suite for core recording engine."""

    def test_01_ffmpeg_and_hardware_detection(self):
        """Verify FFmpeg binary and encoder detection."""
        ffmpeg_bin = get_ffmpeg_binary()
        self.assertTrue(os.path.exists(ffmpeg_bin) or ffmpeg_bin == "ffmpeg", "FFmpeg executable must exist")

        encoders = hardware_detector.get_available_encoders()
        self.assertIsInstance(encoders, list)
        self.assertGreater(len(encoders), 0, "At least one encoder must be detected")
        print(f"\n[Test] Detected Encoders: {encoders}")
        print(f"[Test] Best H264 Encoder: {hardware_detector.get_best_h264_encoder()}")

    def test_02_4k_recording_cycle(self):
        """Test a 3-second recording cycle with 4K UHD resolution and check output file validity."""
        test_output_dir = str(PROJECT_ROOT / "tests" / "test_output")
        os.makedirs(test_output_dir, exist_ok=True)
        settings.set("output_dir", test_output_dir)
        settings.set("resolution", "4K Ultra HD (3840x2160)")
        settings.set("quality_profile", "4K Ultra Master (60 Mbps)")
        settings.set("record_system_audio", False)
        settings.set("record_microphone", False)

        # Region: 640x360 scaled to 4K
        region = {"left": 0, "top": 0, "width": 640, "height": 360}

        print("\n[Test] Starting 3-second 4K Ultra HD recording cycle...")
        started = controller.start_recording(region=region)
        self.assertTrue(started, "Recording controller must start cleanly in 4K mode")

        time.sleep(3.0)

        output_file = controller.current_output_file
        controller.stop_recording()

        # Wait for file finalize
        time.sleep(1.5)

        self.assertIsNotNone(output_file, "Output file path must be set")
        self.assertTrue(os.path.exists(output_file), f"Output file {output_file} must exist")
        file_size = os.path.getsize(output_file)
        self.assertGreater(file_size, 1000, "4K Output file must contain encoded video bytes")
        print(f"[Test] 4K Recording successfully created: {output_file} ({file_size} bytes)")

        # Cleanup
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
