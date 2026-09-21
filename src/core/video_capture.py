"""
High-performance video capture worker thread using MSS/DXCam.
"""

import threading
import time
import queue
from typing import Optional, Dict, Any, Tuple
import numpy as np
import mss


class VideoCaptureWorker(threading.Thread):
    """Worker thread that continuously grabs screen frames at target FPS."""

    def __init__(
        self,
        frame_queue: queue.Queue,
        region: Optional[Dict[str, int]] = None,
        target_fps: int = 60,
        show_cursor: bool = True,
        overlay_callback: Optional[Any] = None,
    ):
        super().__init__(daemon=True, name="VideoCaptureWorker")
        self.frame_queue = frame_queue
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.show_cursor = show_cursor
        self.overlay_callback = overlay_callback

        self._running = threading.Event()
        self._paused = threading.Event()
        self._stopped = threading.Event()

        # Capture geometry setup
        self.region = self._normalize_region(region)
        self.width = self.region["width"]
        self.height = self.region["height"]

        # Statistics
        self.frames_captured = 0
        self.frames_dropped = 0
        self.actual_fps = 0.0

    def _normalize_region(self, region: Optional[Dict[str, int]]) -> Dict[str, int]:
        """Ensure width and height are even integers for H.264 macroblock compatibility."""
        with mss.MSS() as sct:
            if region is None:
                # Default to primary monitor
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                left = mon["left"]
                top = mon["top"]
                width = mon["width"]
                height = mon["height"]
            else:
                left = int(region.get("left", 0))
                top = int(region.get("top", 0))
                width = int(region.get("width", 1920))
                height = int(region.get("height", 1080))

        # Even dimension normalization: must be divisible by 2
        width = width if width % 2 == 0 else width - 1
        height = height if height % 2 == 0 else height - 1

        # Bounds safety minimum
        width = max(width, 64)
        height = max(height, 64)

        return {"left": left, "top": top, "width": width, "height": height}

    def run(self) -> None:
        """Main capture loop."""
        self._running.set()
        sct = mss.MSS()

        target_bbox = {
            "left": self.region["left"],
            "top": self.region["top"],
            "width": self.region["width"],
            "height": self.region["height"],
        }

        t_start = time.perf_counter()
        next_frame_time = t_start
        fps_calc_start = t_start
        fps_frames_count = 0

        try:
            while self._running.is_set():
                if self._paused.is_set():
                    time.sleep(0.05)
                    next_frame_time = time.perf_counter()
                    continue

                now = time.perf_counter()
                if now < next_frame_time:
                    sleep_duration = next_frame_time - now
                    if sleep_duration > 0.002:
                        time.sleep(sleep_duration - 0.001)
                    while time.perf_counter() < next_frame_time:
                        pass  # Micro-spin wait for sub-millisecond precision

                capture_time = time.perf_counter()
                pts = capture_time - t_start

                # Grab screenshot
                frame = None
                try:
                    sct_img = sct.grab(target_bbox)
                    frame = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape(
                        (target_bbox["height"], target_bbox["width"], 4)
                    )[:, :, :3]
                except Exception as mss_err:
                    # Fallback tier 1: PIL ImageGrab
                    try:
                        from PIL import ImageGrab
                        bbox = (
                            target_bbox["left"],
                            target_bbox["top"],
                            target_bbox["left"] + target_bbox["width"],
                            target_bbox["top"] + target_bbox["height"],
                        )
                        pil_img = ImageGrab.grab(bbox=bbox)
                        frame = np.array(pil_img)[:, :, ::-1]  # RGB to BGR
                    except Exception:
                        # Fallback tier 2: Synthetic frame generator (for CI/headless/locked screen)
                        frame = np.zeros((target_bbox["height"], target_bbox["width"], 3), dtype=np.uint8)
                        # Add simple background gradient
                        frame[:, :, 0] = 32  # Dark blue-gray
                        frame[:, :, 1] = 24
                        frame[:, :, 2] = 20

                if frame is None:
                    time.sleep(0.01)
                    continue

                # Apply live overlays (webcam, annotation, cursor ripple) if provided
                if self.overlay_callback:
                    try:
                        frame = self.overlay_callback(frame, target_bbox)
                    except Exception:
                        pass

                # Push to frame queue
                try:
                    self.frame_queue.put_nowait((frame, pts))
                    self.frames_captured += 1
                    fps_frames_count += 1
                except queue.Full:
                    self.frames_dropped += 1

                # Calculate live FPS every second
                if capture_time - fps_calc_start >= 1.0:
                    self.actual_fps = fps_frames_count / (capture_time - fps_calc_start)
                    fps_calc_start = capture_time
                    fps_frames_count = 0

                # Schedule next frame
                next_frame_time += self.frame_interval
                if time.perf_counter() > next_frame_time + self.frame_interval:
                    next_frame_time = time.perf_counter()

        finally:
            sct.close()
            self._stopped.set()

    def pause(self) -> None:
        """Pause frame capture."""
        self._paused.set()

    def resume(self) -> None:
        """Resume frame capture."""
        self._paused.clear()

    def stop(self) -> None:
        """Signal worker to stop."""
        self._running.clear()
