"""
Unit Tests for ROI Processor
Violence District Cooldown Tracker
"""
import unittest
import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from processing.roi_processor import ROIConfig, ROIProcessor


class TestROIProcessor(unittest.TestCase):
    """Pengujian Unit untuk ROI Configuration dan Cropping."""

    def setUp(self):
        # Buat dummy image 1920x1080 (seperti layar Roblox)
        self.frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # Berikan warna unik di area (100, 100) s/d (300, 300)
        self.frame[100:300, 100:300] = (255, 128, 0)

    def test_normal_crop(self):
        config = ROIConfig(x=100, y=100, width=200, height=200)
        processor = ROIProcessor(config)
        cropped = processor.crop(self.frame)

        self.assertIsNotNone(cropped)
        self.assertEqual(cropped.shape, (200, 200, 3))
        # Verifikasi bahwa pixel yang terpotong benar-benar berisi warna yang disiapkan
        self.assertEqual(cropped[0, 0, 0], 255)
        self.assertEqual(cropped[0, 0, 1], 128)

    def test_out_of_bounds_clamping(self):
        """Memastikan koordinat yang melebihi batas layar tidak menyebabkan crash/IndexError."""
        # ROI diletakkan di koordinat 1900x1000 dengan ukuran 200x200 (melebihi 1920x1080)
        config = ROIConfig(x=1900, y=1000, width=200, height=200)
        processor = ROIProcessor(config)
        cropped = processor.crop(self.frame)

        self.assertIsNotNone(cropped)
        # Sisa area yang valid: w = 1920 - 1900 = 20, h = 1080 - 1000 = 80
        self.assertEqual(cropped.shape, (80, 20, 3))

    def test_roi_serialization(self):
        config = ROIConfig(x=50, y=60, width=150, height=120, enabled=True)
        d = config.to_dict()
        loaded = ROIConfig.from_dict(d)

        self.assertEqual(loaded.x, 50)
        self.assertEqual(loaded.y, 60)
        self.assertEqual(loaded.width, 150)
        self.assertEqual(loaded.height, 120)
        self.assertTrue(loaded.enabled)

    def test_disabled_roi(self):
        config = ROIConfig(x=100, y=100, width=200, height=200, enabled=False)
        processor = ROIProcessor(config)
        cropped = processor.crop(self.frame)
        self.assertIsNone(cropped)


if __name__ == "__main__":
    unittest.main()
