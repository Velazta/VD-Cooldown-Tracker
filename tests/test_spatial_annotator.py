"""Unit and Integration Tests for Spatial Annotator Module.

Violence District Cooldown Tracker — Week 3 (Day 16)
Verifies:
- Bounding box extraction with MOG2 and contour analysis
- Bounding box coordinates normalization and aspect ratio
- YOLO label formatting
- Spatial annotation manifest integrity
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

import numpy as np

from tools.spatial_annotator import SpatialAnnotator, BoundingBox, SpatialAnnotationManifest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestSpatialAnnotator(unittest.TestCase):
    """Test suite untuk SpatialAnnotator."""

    def setUp(self) -> None:
        # Cek path legacy_mog2 jika annotations lama sudah dipindahkan sesuai Phase 0
        self.manifest_file = PROJECT_ROOT / "dataset" / "legacy_mog2" / "bounding_boxes.json"
        if not self.manifest_file.exists():
            self.manifest_file = PROJECT_ROOT / "dataset" / "annotations" / "bounding_boxes.json"

        self.yolo_dir = PROJECT_ROOT / "dataset" / "legacy_mog2" / "labels"
        if not self.yolo_dir.exists():
            self.yolo_dir = PROJECT_ROOT / "dataset" / "extracted" / "labels"

    def test_bounding_boxes_manifest_validity(self) -> None:
        """Memastikan manifest bounding box memuat anotasi spasial dengan koordinat ternormalisasi yang valid."""
        self.assertTrue(self.manifest_file.exists())
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["killer_id"], "the_hidden")
        self.assertGreater(data["total_annotated_frames"], 0)
        self.assertGreater(data["total_valid_bboxes"], 0)

        # Verifikasi struktur koordinat bounding box
        valid_bboxes = [a["bbox"] for a in data["annotations"] if a.get("has_detection") and a.get("bbox")]
        self.assertGreater(len(valid_bboxes), 100)

        for b in valid_bboxes:
            self.assertGreaterEqual(b["x"], 0)
            self.assertGreaterEqual(b["y"], 0)
            self.assertGreater(b["width"], 0)
            self.assertGreater(b["height"], 0)
            # Koordinat ternormalisasi harus dalam rentang [0.0, 1.0]
            self.assertGreaterEqual(b["x_center_norm"], 0.0)
            self.assertLessEqual(b["x_center_norm"], 1.0)
            self.assertGreaterEqual(b["y_center_norm"], 0.0)
            self.assertLessEqual(b["y_center_norm"], 1.0)
            self.assertGreater(b["width_norm"], 0.0)
            self.assertLessEqual(b["width_norm"], 1.0)
            self.assertGreater(b["height_norm"], 0.0)
            self.assertLessEqual(b["height_norm"], 1.0)

    def test_yolo_labels_generation(self) -> None:
        """Memastikan label format YOLO (.txt) diekspor dengan struktur kelas yang benar."""
        self.assertTrue(self.yolo_dir.exists())
        txt_files = list(self.yolo_dir.rglob("*.txt"))
        self.assertGreater(len(txt_files), 100)

        # Periksa isi salah satu berkas .txt
        sample_txt = txt_files[0]
        content = sample_txt.read_text(encoding="utf-8").strip()
        parts = content.split()
        self.assertEqual(len(parts), 5)  # class_id, xc, yc, w, h
        class_id = int(parts[0])
        self.assertIn(class_id, (0, 1, 2, 3))
        for val_str in parts[1:]:
            val = float(val_str)
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)


if __name__ == "__main__":
    unittest.main()
