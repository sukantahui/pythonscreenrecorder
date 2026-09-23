"""
Unit tests for locked aspect ratio presets, region selection calculations, and encoder safeguards.
"""

import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QRect
from src.config.constants import ASPECT_RATIO_PRESETS, RESOLUTION_PRESETS
from src.core.ffmpeg_writer import FFmpegWriter


class TestRegionPresets(unittest.TestCase):
    """Test suite for locked aspect ratio capture presets."""

    @classmethod
    def setUpClass(cls):
        # Ensure a single QApplication instance for Qt widget tests
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_01_aspect_ratio_presets_definitions(self):
        """Verify all requested presets exist with valid ratios and even dimensions."""
        required_keys = ["9:16", "16:9", "1:1", "4:5", "4:3", "21:9", "freeform"]
        for key in required_keys:
            self.assertIn(key, ASPECT_RATIO_PRESETS, f"Preset {key} must exist in ASPECT_RATIO_PRESETS")

        # Test locked ratio validity
        for key, info in ASPECT_RATIO_PRESETS.items():
            if key == "freeform":
                self.assertIsNone(info["ratio"])
                continue

            r = info["ratio"]
            self.assertIsInstance(r, (tuple, list))
            self.assertEqual(len(r), 2)
            self.assertGreater(r[0], 0)
            self.assertGreater(r[1], 0)

            expected_ar = r[0] / r[1]

            # Check all listed sizes
            for w, h in info.get("sizes", []):
                self.assertEqual(w % 2, 0, f"{key} size {w}x{h} width must be even")
                self.assertEqual(h % 2, 0, f"{key} size {w}x{h} height must be even")
                actual_ar = w / h
                self.assertAlmostEqual(
                    actual_ar,
                    expected_ar,
                    delta=0.08,
                    msg=f"{key} resolution {w}x{h} must conform to aspect ratio {expected_ar:.3f}",
                )

    def test_02_overlay_ratio_locking_and_resizing(self):
        """Verify RegionSelectorOverlay aspect ratio locking and handle resizing."""
        from src.overlays.region_selector import RegionSelectorOverlay

        overlay = RegionSelectorOverlay()

        # Open with 9:16 (Reel / Shorts)
        overlay.open_with_ratio("9:16")
        self.assertTrue(overlay.is_ratio_locked)
        self.assertEqual(overlay.current_ratio_key, "9:16")

        r = overlay.selection_rect.normalized()
        ar_9_16 = 9 / 16
        actual_ar = r.width() / r.height()
        self.assertAlmostEqual(actual_ar, ar_9_16, delta=0.03, msg="Initial rect must match 9:16")
        self.assertEqual(r.width() % 2, 0)
        self.assertEqual(r.height() % 2, 0)

        # Simulate resizing via Bottom-Right handle
        overlay.is_resizing = True
        overlay.current_handle = overlay.HANDLE_BR
        overlay.drag_start_pos = r.bottomRight()
        overlay.initial_rect = QRect(r)

        # Move mouse diagonally outward
        new_mouse_pos = r.bottomRight() + QPoint(100, 200)
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtCore import QEvent

        # Call mouseMove with locked ratio
        class DummyEvent:
            def __init__(self, pt):
                self._pt = pt
            def pos(self):
                return self._pt

        overlay.mouseMoveEvent(DummyEvent(new_mouse_pos))

        resized = overlay.selection_rect.normalized()
        self.assertEqual(resized.width() % 2, 0, "Resized width must be even")
        self.assertEqual(resized.height() % 2, 0, "Resized height must be even")
        self.assertAlmostEqual(
            resized.width() / resized.height(),
            ar_9_16,
            delta=0.03,
            msg="Resized rect must strictly maintain 9:16 aspect ratio",
        )

        overlay.close()

    def test_03_overlay_confirm_signal(self):
        """Verify that confirming selection emits complete metadata."""
        from src.overlays.region_selector import RegionSelectorOverlay

        overlay = RegionSelectorOverlay()
        overlay.open_with_ratio("1:1")

        received_region = None
        def on_selected(region):
            nonlocal received_region
            received_region = region

        overlay.region_selected.connect(on_selected)
        overlay._confirm()

        self.assertIsNotNone(received_region)
        self.assertEqual(received_region["ratio_key"], "1:1")
        self.assertEqual(received_region["width"] % 2, 0)
        self.assertEqual(received_region["height"] % 2, 0)
        self.assertAlmostEqual(received_region["width"] / received_region["height"], 1.0, delta=0.02)
        self.assertIn("ratio_name", received_region)

        overlay.close()

    def test_04_ffmpeg_writer_aspect_ratio_guard(self):
        """Verify FFmpegWriter prevents distortion when capture AR differs from global preset."""
        # Case 1: Reel capture (1080x1920, 9:16) with 4K Landscape preset (3840x2160, 16:9)
        writer_vertical = FFmpegWriter(
            output_filepath="dummy.mp4",
            width=1080,
            height=1920,
            fps=60,
            target_resolution="4K Ultra HD (3840x2160)",
        )
        # Should NOT scale to (3840, 2160) because aspect ratios conflict!
        dims = writer_vertical._resolve_target_dimensions()
        self.assertEqual(dims, (1080, 1920), "Must preserve vertical 9:16 dimensions without stretching to 16:9")

        # Case 2: Matching aspect ratio 16:9 (1920x1080) with 4K Landscape (3840x2160)
        writer_matching = FFmpegWriter(
            output_filepath="dummy.mp4",
            width=1920,
            height=1080,
            fps=60,
            target_resolution="4K Ultra HD (3840x2160)",
        )
        dims_match = writer_matching._resolve_target_dimensions()
        self.assertEqual(dims_match, (3840, 2160), "Matching aspect ratio should scale to target resolution")

        # Case 3: Native / None resolution
        writer_native = FFmpegWriter(
            output_filepath="dummy.mp4",
            width=1080,
            height=1350,
            fps=60,
            target_resolution=None,
        )
        self.assertEqual(writer_native._resolve_target_dimensions(), (1080, 1350))

    def test_05_overlay_moveable_selection(self):
        """Verify that selection box is draggable/moveable via mouse and keyboard."""
        from src.overlays.region_selector import RegionSelectorOverlay
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent

        overlay = RegionSelectorOverlay()
        overlay.open_with_ratio("16:9")

        r = overlay.selection_rect.normalized()
        center = r.center()

        # 1. Clicking inside box must return HANDLE_MOVE
        handle = overlay._get_handle_at(center)
        self.assertEqual(handle, overlay.HANDLE_MOVE, "Clicking inside selection must detect HANDLE_MOVE")

        # 2. Simulate dragging to move
        overlay.is_resizing = True
        overlay.current_handle = overlay.HANDLE_MOVE
        overlay.drag_start_pos = center
        overlay.initial_rect = QRect(r)

        class DummyEvent:
            def __init__(self, pt):
                self._pt = pt
            def pos(self):
                return self._pt

        # Drag by +50, +30
        overlay.mouseMoveEvent(DummyEvent(center + QPoint(50, 30)))

        moved = overlay.selection_rect.normalized()
        self.assertEqual(moved.left(), r.left() + 50)
        self.assertEqual(moved.top(), r.top() + 30)
        self.assertEqual(moved.width(), r.width())
        self.assertEqual(moved.height(), r.height())

        # 3. Test keyboard arrow keys
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        overlay.keyPressEvent(key_event)
        self.assertEqual(overlay.selection_rect.left(), moved.left() + 2)

        overlay.close()


if __name__ == "__main__":
    unittest.main()

