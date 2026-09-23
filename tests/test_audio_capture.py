"""
Unit and integration tests for audio capture, webcam microphone detection, and mixing.
"""

import sys
import os
import time
import queue
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.audio_capture import AudioCaptureWorker
from src.core.camera_detect import camera_detector


class TestAudioCapture(unittest.TestCase):
    """Test suite for audio devices and webcam sound capture."""

    def test_01_device_discovery_and_webcam_tagging(self):
        """Verify audio device discovery and webcam microphone tagging."""
        devices = AudioCaptureWorker.get_audio_devices()
        self.assertIn("microphones", devices)
        self.assertIn("webcam_microphones", devices)

        print(f"\n[Test] Found {len(devices['microphones'])} total microphones.")
        print(f"[Test] Found {len(devices['webcam_microphones'])} webcam microphones.")

        for w in devices["webcam_microphones"]:
            self.assertTrue(w["is_webcam"], f"Device {w['name']} must be marked as webcam")
            print(f"  * Webcam mic: {w['name']} (ID: {w['id']})")

    def test_02_webcam_matching(self):
        """Test automatic matching between connected webcams and audio devices."""
        cameras = camera_detector.get_available_cameras()
        if cameras:
            cam_name = cameras[0]["name"]
            matched_id = AudioCaptureWorker.match_webcam_audio(cam_name)
            print(f"\n[Test] Camera '{cam_name}' matched audio device ID: {matched_id}")
            if "iriun" in cam_name.lower():
                self.assertIsNotNone(matched_id, "Iriun Webcam should match its audio device")

    def test_03_worker_webcam_capture_cycle(self):
        """Test AudioCaptureWorker stream startup and capture with webcam audio enabled."""
        q = queue.Queue(maxsize=100)
        webcam_id = AudioCaptureWorker.match_webcam_audio("Iriun Webcam")

        worker = AudioCaptureWorker(
            audio_queue=q,
            record_system_audio=False,
            record_mic=False,
            record_webcam_audio=webcam_id is not None,
            webcam_audio_device_id=webcam_id,
            webcam_volume=1.0,
        )

        worker.start()
        time.sleep(1.0)
        worker.stop()

        print(f"\n[Test] Audio worker ran with webcam_id={webcam_id}, captured chunks={q.qsize()}")


if __name__ == "__main__":
    unittest.main()
