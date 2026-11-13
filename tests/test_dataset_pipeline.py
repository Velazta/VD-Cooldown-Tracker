"""Unit and Integration Tests for Dataset Indexer & Pipeline (V2).

Violence District Cooldown Tracker — Week 3 (Day 15)
Verifies:
- Semantic classification of Leap positives vs hard negatives with subcategories and splits
- Accurate metadata extraction from real MP4 videos, PNG images, and WAV audio
- SHA-256 cryptographic checksum calculation
- Skin HSV color profiling
- Audio FFT spectral centroid and dominant frequency calculation
- Full integrity diagnostic audit
- Catalog JSON serialization and schema validity
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from tools.dataset_indexer import (
    DatasetIndexer,
    DatasetCatalog,
    VideoEntry,
    ImageEntry,
    SkinEntry,
    AudioEntry,
    compute_sha256,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestDatasetPipeline(unittest.TestCase):
    """Test suite untuk DatasetIndexer dan metadata manifest."""

    def setUp(self) -> None:
        self.indexer = DatasetIndexer(root_path=PROJECT_ROOT / "database" / "dataset" / "HIDDEN")

    def test_classify_video_semantics(self) -> None:
        """Memastikan klasifikasi video membedakan aksi Leap positif vs negatif beserta split."""
        cat, sub, split, is_pos = self.indexer.classify_video("hidden1_leap_skill.mp4")
        self.assertEqual(cat, "leap_action")
        self.assertEqual(sub, "leap_solo")
        self.assertEqual(split, "train")
        self.assertTrue(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_video("hidden_leap+mark_comboskill.mp4")
        self.assertEqual(cat, "leap_action")
        self.assertEqual(sub, "leap_mark_combo")
        self.assertEqual(split, "test")
        self.assertTrue(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_video("hidden1_basic_hit_survivor.mp4")
        self.assertEqual(cat, "basic_attack")
        self.assertEqual(sub, "hit_survivor")
        self.assertEqual(split, "train")
        self.assertFalse(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_video("hidden_movement_chasing.mp4")
        self.assertEqual(cat, "chasing_movement")
        self.assertEqual(sub, "chase_running")
        self.assertEqual(split, "test")
        self.assertFalse(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_video("hidden2_mark_skill.mp4")
        self.assertEqual(cat, "mark_action")
        self.assertEqual(sub, "mark_solo")
        self.assertEqual(split, "train")
        self.assertFalse(is_pos)

    def test_classify_image_semantics(self) -> None:
        """Memastikan klasifikasi gambar memisahkan still aksi leap, mark, dan stay."""
        cat, sub, split, is_pos = self.indexer.classify_image("hidden_leap.png")
        self.assertEqual(cat, "leap")
        self.assertEqual(split, "train")
        self.assertTrue(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_image("hidden_mark4.png")
        self.assertEqual(cat, "mark")
        self.assertEqual(split, "train")
        self.assertFalse(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_image("hidden_stay.png")
        self.assertEqual(cat, "stay")
        self.assertEqual(split, "train")
        self.assertFalse(is_pos)

    def test_classify_audio_semantics(self) -> None:
        """Memastikan klasifikasi audio memisahkan suara Leap vs serangan lain."""
        cat, sub, split, is_pos = self.indexer.classify_audio("hidden_leap_var1.wav")
        self.assertEqual(cat, "leap_cue")
        self.assertEqual(sub, "vocal_and_whoosh")
        self.assertEqual(split, "train")
        self.assertTrue(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_audio("hidden_basic_attack.wav")
        self.assertEqual(cat, "attack_cue")
        self.assertEqual(sub, "blade_slash")
        self.assertEqual(split, "train")
        self.assertFalse(is_pos)

        cat, sub, split, is_pos = self.indexer.classify_audio("hidden_mark_hit_wall.wav")
        self.assertEqual(cat, "mark_cue")
        self.assertEqual(sub, "spear_hit_wall")
        self.assertEqual(split, "val")
        self.assertFalse(is_pos)

    def test_indexer_real_scan_completeness_and_features(self) -> None:
        """Memverifikasi pemindaian dataset riil The Hidden menghasilkan metadata mendalam."""
        catalog = self.indexer.build_catalog()

        # Verifikasi jumlah berkas
        self.assertEqual(catalog.killer_id, "the_hidden")
        self.assertEqual(catalog.schema_version, 2)
        self.assertEqual(catalog.total_videos, 18)
        self.assertEqual(catalog.total_ingame_images, 11)
        self.assertEqual(catalog.total_skin_variations, 13)
        self.assertEqual(catalog.total_skin_images, 52)
        self.assertEqual(catalog.total_audio_samples, 5)

        # Verifikasi distribusi split
        self.assertGreater(catalog.train_samples_count, 0)
        self.assertGreater(catalog.val_samples_count, 0)
        self.assertGreater(catalog.test_samples_count, 0)
        self.assertEqual(
            catalog.train_samples_count + catalog.val_samples_count + catalog.test_samples_count,
            catalog.total_videos + catalog.total_ingame_images + catalog.total_audio_samples,
        )

        # Verifikasi metadata video dan SHA-256
        for v in catalog.videos:
            self.assertEqual(v.width, 1280)
            self.assertEqual(v.height, 720)
            self.assertIn(v.fps, (30.0, 60.0))
            self.assertGreater(v.frame_count, 0)
            self.assertGreater(v.file_size_bytes, 0)
            self.assertEqual(len(v.sha256), 64)
            self.assertEqual(v.aspect_ratio, "16:9")
            self.assertGreater(v.bitrate_kbps, 0.0)

        # Verifikasi profil warna skin
        for s in catalog.skins:
            self.assertEqual(len(s.sha256), 64)
            self.assertEqual(len(s.mean_hsv), 3)
            self.assertEqual(len(s.mean_bgr), 3)
            # Hue dalam OpenCV berkisar 0-179
            self.assertGreaterEqual(s.mean_hsv[0], 0.0)
            self.assertLessEqual(s.mean_hsv[0], 179.0)

        # Verifikasi audio FFT dan energi
        for a in catalog.audio:
            self.assertEqual(a.sample_rate_hz, 44100)
            self.assertEqual(a.channels, 2)
            self.assertGreater(a.duration_seconds, 3.0)
            self.assertGreater(a.peak_amplitude, 0)
            self.assertGreater(a.rms_energy, 0.0)
            self.assertGreater(a.dominant_frequency_hz, 0.0)
            self.assertGreater(a.spectral_centroid_hz, 0.0)
            self.assertLess(a.energy_dbfs, 0.0)  # Selalu negatif relatif terhadap full-scale
            self.assertEqual(len(a.sha256), 64)

        # Verifikasi kontras akustik: Centroid Leap jauh lebih rendah dari Basic Attack
        leap_audio = next(a for a in catalog.audio if a.is_positive_leap)
        attack_audio = next(a for a in catalog.audio if a.file_name == "hidden_basic_attack.wav")
        self.assertLess(leap_audio.spectral_centroid_hz, 4000.0)
        self.assertGreater(attack_audio.spectral_centroid_hz, 7000.0)

    def test_verify_integrity_diagnostics(self) -> None:
        """Memastikan audit integritas dataset menghasilkan status PASS tanpa korupsi/duplikat."""
        report = self.indexer.verify_integrity()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["total_files_scanned"], 86)
        self.assertEqual(len(report["corrupt_files"]), 0)
        self.assertEqual(len(report["duplicate_files"]), 0)
        self.assertTrue(report["video_decodable"])
        self.assertTrue(report["audio_pcm_valid"])
        self.assertTrue(report["images_valid"])

    def test_save_catalog_json_serialization(self) -> None:
        """Memastikan katalog dapat disimpan ke disk dan dimuat ulang tanpa kehilangan data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_catalog.json"
            catalog = self.indexer.save_catalog(out_file)

            self.assertTrue(out_file.exists())
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["killer_id"], "the_hidden")
            self.assertEqual(data["total_videos"], 18)
            self.assertEqual(data["total_audio_samples"], 5)
            self.assertEqual(len(data["videos"]), 18)
            self.assertEqual(len(data["skins"]), 52)
            self.assertIn("dominant_frequency_hz", data["audio"][0])
            self.assertIn("sha256", data["videos"][0])


if __name__ == "__main__":
    unittest.main()
