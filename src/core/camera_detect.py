"""
Camera hardware detection and enumeration service.
Supports DirectShow, QtMultimedia (PyQt6), and OpenCV video inputs.
"""

import sys
import logging
from typing import List, Dict, Any, Optional
import cv2

logger = logging.getLogger(__name__)


class CameraDetector:
    """Detects and enumerates video capture devices on the system."""

    @staticmethod
    def get_available_cameras() -> List[Dict[str, Any]]:
        """
        Enumerate all connected webcam / video capture devices.
        Returns a list of dicts:
        [
            {"id": 0, "name": "Iriun Webcam", "is_default": False},
            ...
        ]
        """
        cameras = []

        # 1. Primary Method: PyQt6 QMediaDevices (Retrieves friendly DirectShow device names)
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            video_inputs = QMediaDevices.videoInputs()
            if video_inputs:
                for idx, cam in enumerate(video_inputs):
                    name = cam.description() or f"Camera {idx}"
                    is_def = cam.isDefault()
                    cameras.append({
                        "id": idx,
                        "name": name,
                        "is_default": is_def,
                        "device_id_str": cam.id().data().decode("utf-8", errors="ignore") if hasattr(cam.id(), "data") else str(cam.id())
                    })
                if cameras:
                    return cameras
        except Exception as e:
            logger.warning(f"QMediaDevices camera enumeration warning: {e}")

        # 2. Fallback Method: OpenCV DirectShow Probe (indices 0 to 5)
        try:
            for idx in range(6):
                backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
                cap = cv2.VideoCapture(idx, backend)
                if not cap.isOpened() and backend != 0:
                    cap = cv2.VideoCapture(idx)

                if cap.isOpened():
                    # Read frame to confirm it is usable
                    ret, _ = cap.read()
                    cap.release()
                    cameras.append({
                        "id": idx,
                        "name": f"Camera {idx} (DirectShow)",
                        "is_default": idx == 0,
                    })
        except Exception as e:
            logger.error(f"OpenCV camera probe error: {e}")

        # 3. If no cameras were found, provide fallback placeholder entry
        if not cameras:
            cameras.append({
                "id": 0,
                "name": "Default Camera (Device 0)",
                "is_default": True
            })

        return cameras

    @staticmethod
    def probe_camera(device_id: int) -> bool:
        """Verify if a specific camera index can be opened and read."""
        try:
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
            cap = cv2.VideoCapture(device_id, backend)
            if not cap.isOpened():
                cap = cv2.VideoCapture(device_id)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                return ret
            return False
        except Exception:
            return False


    @classmethod
    def get_preferred_camera(cls, prefer_iriun: bool = True) -> Dict[str, Any]:
        """Get the preferred camera, prioritizing Iriun Webcam by default."""
        cameras = cls.get_available_cameras()
        if not cameras:
            return {"id": 0, "name": "Default Camera (Device 0)", "is_default": True}

        if prefer_iriun:
            for cam in cameras:
                if any(k in cam["name"].lower() for k in ("iriun", "irium")):
                    return cam

        for cam in cameras:
            if cam.get("is_default", False):
                return cam

        return cameras[0]


camera_detector = CameraDetector()
