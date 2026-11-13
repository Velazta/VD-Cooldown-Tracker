"""Unit Tests for DatasetAnnotator Module.

Violence District Cooldown Tracker — Week 5 (Day 26)
Verifies:
- Loading of spatial bounding box annotations.
- Bounding box coordinate transformations during image augmentations (hflip, rotate, illumination).
- YOLO labeling format (.txt: class xc yc w h).
- Proper Train/Val splitting and dataset.yaml generation.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from tools.dataset_annotator import AnnotationSample, DatasetAnnotator, DatasetSplitSummary

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestDatasetAnnotator(unittest.TestCase):
    """Test suite untuk DatasetAnnotator."""

    def setUp(self) -> None:
        self.annotator = DatasetAnnotator()

    def test_load_base_annotations(self) -> None:
        """Memverifikasi pemuatan sampel anotasi valid dari file JSON."""
        samples = self.annotator.load_base_annotations()
        self.assertGreater(len(samples), 0)
        first = samples[0]
        self.assertIsInstance(first, AnnotationSample)
        self.assertTrue(first.image_path.exists())
        self.assertEqual(len(first.boxes), 1)

        cid, xc, yc, w, h = first.boxes[0]
        self.assertEqual(cid, 0)
        self.assertGreaterEqual(xc, 0.0)
        self.assertLessEqual(xc, 1.0)
        self.assertGreaterEqual(yc, 0.0)
        self.assertLessEqual(yc, 1.0)

    def test_hflip_augmentation_coordinate_math(self) -> None:
        """Memverifikasi bahwa horizontal flip membalik x_center secara matematis: 1.0 - xc."""
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        box = (0, 0.30, 0.50, 0.20, 0.40)

        aug_img, new_box = self.annotator.augment_sample(dummy_img, box, "hflip")
        cid, n_xc, n_yc, n_w, n_h = new_box

        self.assertEqual(cid, 0)
        self.assertAlmostEqual(n_xc, 0.70, places=4)
        self.assertAlmostEqual(n_yc, 0.50, places=4)
        self.assertEqual(n_w, 0.20)
        self.assertEqual(n_h, 0.40)

    def test_illumination_augmentations(self) -> None:
        """Memverifikasi transformasi kecerahan (darker/brighter) mempertahankan bounding box."""
        dummy_img = np.full((50, 50, 3), 120, dtype=np.uint8)
        box = (0, 0.5, 0.5, 0.3, 0.3)

        dark_img, dark_box = self.annotator.augment_sample(dummy_img, box, "darker")
        self.assertEqual(dark_box, box)
        self.assertLess(dark_img.mean(), dummy_img.mean())

        bright_img, bright_box = self.annotator.augment_sample(dummy_img, box, "brighter")
        self.assertEqual(bright_box, box)
        self.assertGreater(bright_img.mean(), dummy_img.mean())

    def test_build_dataset_mini_integration(self) -> None:
        """Menjalankan pembagian dataset skala mini di direktori sementara."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "test_yolo_ds"
            mini_annotator = DatasetAnnotator(output_dir=out_path, train_ratio=0.75)

            summary = mini_annotator.build_dataset()
            self.assertIsInstance(summary, DatasetSplitSummary)
            self.assertGreater(summary.total_images, 10)
            self.assertTrue((out_path / "dataset.yaml").exists())
            self.assertTrue((out_path / "dataset_summary.json").exists())
            self.assertTrue((out_path / "images" / "train").exists())
            self.assertTrue((out_path / "labels" / "train").exists())


if __name__ == "__main__":
    unittest.main()
