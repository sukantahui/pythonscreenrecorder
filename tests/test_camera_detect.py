"""
Unit tests for Camera Detection and Webcam Overlay configuration.
"""

import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from src.core.camera_detect import camera_detector, CameraDetector
from src.config.settings_manager import settings


class TestCameraDetection(unittest.TestCase):
    """Test camera enumeration and settings."""

    @classmethod
    def setUpClass(cls):
        # Ensure QApplication instance exists for QMediaDevices
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_01_enumerate_cameras(self):
        """Test camera discovery returns valid device list."""
        cameras = camera_detector.get_available_cameras()
        self.assertIsInstance(cameras, list)
        self.assertGreater(len(cameras), 0, "Camera detector should return at least one device or fallback")
        print(f"\n[Test] Detected Cameras: {cameras}")

        for cam in cameras:
            self.assertIn("id", cam)
            self.assertIn("name", cam)
            self.assertIsInstance(cam["id"], int)
            self.assertIsInstance(cam["name"], str)

    def test_02_webcam_settings_defaults(self):
        """Test default webcam settings."""
        self.assertIn("webcam_enabled", settings.settings)
        self.assertIn("webcam_device_id", settings.settings)
        self.assertIn("webcam_shape", settings.settings)
        self.assertIn("webcam_size", settings.settings)
        self.assertIn("webcam_mirrored", settings.settings)

    def test_03_camera_probe(self):
        """Test probe_camera helper function."""
        # Probing should not raise an unhandled exception
        result = camera_detector.probe_camera(0)
        self.assertIsInstance(result, bool)
        print(f"[Test] Camera 0 probe result: {result}")


if __name__ == "__main__":
    unittest.main()
