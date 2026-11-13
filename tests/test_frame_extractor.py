"""Unit and Integration Tests for Frame Extractor Module.

Violence District Cooldown Tracker — Week 3 (Day 15 Langkah 2)
Verifies:
- Configurable sampling intervals based on target FPS
- Motion difference (delta motion) calculation
- Correct split/label directory structure creation
- Manifest JSON generation with SHA-256 checksums
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

import cv2
import numpy as np

from tools.extract_dataset import FrameExtractor, FrameMetadata, ExtractionManifest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestFrameExtractor(unittest.TestCase):
    """Test suite untuk FrameExtractor."""

    def setUp(self) -> None:
        self.catalog_path = PROJECT_ROOT / "dataset" / "catalog.json"

    def test_extractor_initialization(self) -> None:
        """Memastikan inisialisasi FrameExtractor dengan konfigurasi default."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "extracted"
            extractor = FrameExtractor(
                catalog_path=self.catalog_path,
                output_dir=out_dir,
                target_fps=10.0,
                image_format="jpg",
            )
            catalog = extractor.load_catalog()
            self.assertEqual(catalog["killer_id"], "the_hidden")
            self.assertEqual(len(catalog["videos"]), 18)

    def test_extract_single_video_synthetic(self) -> None:
        """Memverifikasi ekstraksi frame, kalkulasi motion delta, dan penyimpanan citra pada video sintetis."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            video_file = tmp_path / "test_leap.mp4"
            out_dir = tmp_path / "extracted"

            # Buat video sintetis (10 frame, 30 FPS, resolusi 320x240)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(video_file), fourcc, 30.0, (320, 240))
            for i in range(10):
                # Frame dengan intensitas piksel bervariasi untuk mensimulasikan motion diff
                val = i * 25
                frame = np.full((240, 320, 3), val, dtype=np.uint8)
                out.write(frame)
            out.release()

            video_info = {
                "file_name": "test_leap.mp4",
                "relative_path": str(video_file),
                "is_positive_leap": True,
                "split": "train",
                "category": "leap_action",
                "sub_category": "leap_solo",
            }

            extractor = FrameExtractor(
                output_dir=out_dir,
                target_fps=10.0,  # 30 fps / 10 target fps = step 3
                image_format="jpg",
            )

            frames_meta, max_motion, peak_idx = extractor.extract_from_video(video_info, video_file)

            # Pada 10 frame dengan step 3 (0, 3, 6, 9), seharusnya terekstrak 4 frame
            self.assertEqual(len(frames_meta), 4)
            self.assertGreater(max_motion, 0.0)
            self.assertEqual(frames_meta[0].label, "positive_leap")
            self.assertEqual(frames_meta[0].split, "train")

            # Verifikasi berkas fisik tersimpan di subdirektori yang benar
            expected_file = out_dir / "train" / "positive_leap" / "test_leap_f00000.jpg"
            self.assertTrue(expected_file.exists())
            self.assertEqual(len(frames_meta[0].sha256), 64)

    def test_extract_real_video_filter(self) -> None:
        """Menguji ekstraksi nyata dengan filter 1 video Leap nyata (hidden3_leap_skills.mp4, 77 frames)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "extracted"
            extractor = FrameExtractor(
                catalog_path=self.catalog_path,
                output_dir=out_dir,
                target_fps=5.0,  # 5 FPS untuk uji cepat
                image_format="jpg",
            )

            manifest = extractor.run(filter_substr="hidden3_leap_skills")

            self.assertEqual(manifest.total_frames_extracted, 13)
            # Dengan temporal windowing: 9 frame fase aktif Leap, 4 frame recovery/idle
            self.assertEqual(manifest.positive_leap_frames, 9)
            self.assertEqual(manifest.negative_action_frames, 4)

            # Verifikasi manifest tersimpan di disk
            manifest_file = out_dir / "manifest.json"
            self.assertTrue(manifest_file.exists())
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["total_frames_extracted"], 13)


if __name__ == "__main__":
    unittest.main()
