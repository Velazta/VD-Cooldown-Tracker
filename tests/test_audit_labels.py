"""Unit tests for tools/audit_labels.py.

Violence District Cooldown Tracker â€” Detector Rebuild (Phase 0)
"""

import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from tools.audit_labels import check_ultralytics_pairing, run_label_audit


class TestAuditLabels(unittest.TestCase):
    """Test suite for audit_labels functionality."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_check_ultralytics_pairing_valid(self) -> None:
        """Memastikan check_ultralytics_pairing mendeteksi pasangan /images/ <-> /labels/."""
        img_dir = self.test_root / "dataset" / "images" / "train"
        lbl_dir = self.test_root / "dataset" / "labels" / "train"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        img_path = img_dir / "sample_001.jpg"
        lbl_path = lbl_dir / "sample_001.txt"
        img_path.touch()
        lbl_path.touch()

        paired, target_lbl, rule = check_ultralytics_pairing(img_path)
        self.assertTrue(paired)
        self.assertEqual(target_lbl, lbl_path)
        self.assertEqual(rule, "images_to_labels_rule")

    def test_check_ultralytics_pairing_missing_images_folder(self) -> None:
        """Memastikan path tanpa /images/ dilaporkan gagal konvensi Ultralytics."""
        img_dir = self.test_root / "dataset" / "extracted" / "train" / "leap"
        img_dir.mkdir(parents=True, exist_ok=True)
        img_path = img_dir / "sample_001.jpg"
        img_path.touch()

        paired, _, rule = check_ultralytics_pairing(img_path)
        self.assertFalse(paired)
        self.assertEqual(rule, "missing_images_folder_in_path")

    def test_run_label_audit_synthetic(self) -> None:
        """Memastikan run_label_audit menghitung statistik secara presisi."""
        # Buat dummy bounding_boxes.json
        dummy_data = {
            "schema_version": 1,
            "annotations": [
                {
                    "frame_id": "frame_0.jpg",
                    "relative_image_path": "extracted/train/leap/frame_0.jpg",
                    "phase": "leap_airborne",
                    "class_id": 0,
                    "bbox": [10, 20, 30, 40],
                    "has_detection": True,
                },
                {
                    "frame_id": "frame_1.jpg",
                    "relative_image_path": "extracted/train/leap/frame_1.jpg",
                    "phase": "leap_airborne",
                    "class_id": 0,
                    "bbox": None,
                    "has_detection": False,
                },
                {
                    "frame_id": "frame_2.jpg",
                    "relative_image_path": "extracted/train/mark/frame_2.jpg",
                    "phase": "mark_active",
                    "class_id": 3,
                    "bbox": [5, 5, 20, 20],
                    "has_detection": True,
                },
            ]
        }
        json_path = self.test_root / "bounding_boxes.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f)

        # Buat dummy gambar agar overlay bisa digambar
        img_dir = self.test_root / "extracted" / "train" / "leap"
        img_dir.mkdir(parents=True, exist_ok=True)
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(img_dir / "frame_0.jpg"), dummy_img)

        report_path = self.test_root / "audit_report.md"
        overlay_dir = self.test_root / "overlays"

        res = run_label_audit(
            bbox_json_path=json_path,
            extracted_dir=self.test_root,
            output_report_path=report_path,
            overlay_dir=overlay_dir,
            max_overlays=5,
        )

        self.assertEqual(res["total_frames"], 3)
        self.assertEqual(res["total_with_box"], 2)
        self.assertEqual(res["total_empty"], 1)
        self.assertEqual(res["leap_phases"]["leap_airborne"]["total"], 2)
        self.assertEqual(res["leap_phases"]["leap_airborne"]["with_box"], 1)
        self.assertEqual(res["leap_phases"]["leap_airborne"]["empty"], 1)
        self.assertEqual(res["class3_composition"]["mark_active"], 1)

        self.assertTrue(report_path.exists())
        self.assertGreater(res["overlays_generated"], 0)

    def test_run_label_audit_file_not_found(self) -> None:
        """Memastikan run_label_audit raise FileNotFoundError jika file tidak ada."""
        with self.assertRaises(FileNotFoundError):
            run_label_audit(self.test_root / "non_existent.json")


if __name__ == "__main__":
    unittest.main()
