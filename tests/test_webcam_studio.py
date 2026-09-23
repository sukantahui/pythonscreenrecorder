"""
Unit and integration tests for Studio-Grade Webcam PiP upgrades:
- Aspect ratio dimension math (16:9 Wide, 1:1 Circle/Rounded/Square, 9:16 Portrait)
- Real-time studio lighting & color filters (Normal, Warm, Cool, Bright, B&W, Beauty)
- Corner docking and cycling
- Shape cycling and filter cycling
"""

import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QRect
import numpy as np
import cv2

# Ensure QApplication exists for GUI overlay tests
app = QApplication.instance()
if app is None:
    app = QApplication([])

from src.config.constants import WEBCAM_SHAPES, WEBCAM_FILTERS, WEBCAM_BORDER_THEMES
from src.overlays.webcam_pip import WebcamPiPOverlay


class TestWebcamStudio(unittest.TestCase):
    """Test suite for webcam overlay studio features."""

    def setUp(self):
        self.overlay = WebcamPiPOverlay(
            device_id=0,
            shape="wide",
            size=220,
            mirrored=True,
            filter_name="normal",
            border_theme="indigo",
        )

    def tearDown(self):
        self.overlay.stop()

    def test_aspect_ratio_dimensions(self):
        """Verify dynamic aspect ratio calculation for all shapes."""
        # 16:9 Widescreen
        self.overlay.set_shape("wide")
        w, h = self.overlay._get_pip_dimensions()
        self.assertEqual(h, 220)
        self.assertEqual(w, int(220 * 16 / 9))

        # 9:16 Vertical Reel
        self.overlay.set_shape("portrait")
        w, h = self.overlay._get_pip_dimensions()
        self.assertEqual(w, 220)
        self.assertEqual(h, int(220 * 16 / 9))

        # 1:1 Shapes
        for shape in ["circle", "rounded", "square"]:
            self.overlay.set_shape(shape)
            w, h = self.overlay._get_pip_dimensions()
            self.assertEqual(w, 220)
            self.assertEqual(h, 220)

    def test_studio_filters_execution(self):
        """Verify that all studio lighting and color filters process frames without error."""
        test_frame = np.full((720, 1280, 3), 120, dtype=np.uint8)

        for filter_key in WEBCAM_FILTERS.keys():
            self.overlay.set_filter(filter_key)
            result = self.overlay._apply_filter(test_frame)
            self.assertIsNotNone(result)
            self.assertEqual(result.shape, (720, 1280, 3))
            self.assertEqual(result.dtype, np.uint8)

    def test_shape_cycling(self):
        """Verify cycle_shape rotates through all shapes in WEBCAM_SHAPES."""
        shapes_order = list(WEBCAM_SHAPES.keys())
        self.overlay.set_shape(shapes_order[0])

        for expected_shape in shapes_order[1:] + [shapes_order[0]]:
            self.overlay.cycle_shape()
            self.assertEqual(self.overlay.shape_type, expected_shape)

    def test_filter_cycling(self):
        """Verify cycle_filter rotates through all filters in WEBCAM_FILTERS."""
        filters_order = list(WEBCAM_FILTERS.keys())
        self.overlay.set_filter(filters_order[0])

        for expected_filter in filters_order[1:] + [filters_order[0]]:
            self.overlay.cycle_filter()
            self.assertEqual(self.overlay.filter_type, expected_filter)

    def test_border_themes(self):
        """Verify setting border themes."""
        for theme_key in WEBCAM_BORDER_THEMES.keys():
            self.overlay.set_border_theme(theme_key)
            self.assertEqual(self.overlay.border_theme, theme_key)

    def test_corner_docking(self):
        """Verify 1-click corner docking execution."""
        for corner in ["bottom-right", "bottom-left", "top-right", "top-left"]:
            self.overlay.snap_to_corner(corner)
            pos = self.overlay.pos()
            self.assertIsInstance(pos, QPoint)


if __name__ == "__main__":
    unittest.main()
