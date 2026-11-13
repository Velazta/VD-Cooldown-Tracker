"""Unit and Integration Tests for Temporal Action Annotations.

Violence District Cooldown Tracker — Week 3 (Day 15 Refinement)
Verifies:
- Integrity and continuity of temporal action windows in dataset/temporal_annotations.json
- Prevention of label noise (pre-idle frames marked negative, airborne frames marked positive)
- Extraction manifest reflects distinct leap phases (windup, airborne, landing)
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestTemporalAnnotations(unittest.TestCase):
    """Test suite untuk temporal action annotations."""

    def setUp(self) -> None:
        self.annot_file = PROJECT_ROOT / "dataset" / "temporal_annotations.json"
        self.manifest_file = PROJECT_ROOT / "dataset" / "extracted" / "manifest.json"

    def test_temporal_annotations_schema_and_continuity(self) -> None:
        """Memastikan rentang frame tiap video valid, runtut, dan tidak saling tumpang tindih."""
        self.assertTrue(self.annot_file.exists())
        with open(self.annot_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["killer_id"], "the_hidden")
        self.assertIn("videos", data)

        videos = data["videos"]
        self.assertEqual(len(videos), 6)  # 6 rekaman Leap

        for vname, vdata in videos.items():
            fps = vdata["fps"]
            total_fc = vdata["total_frames"]
            self.assertEqual(fps, 30.0)
            self.assertGreater(total_fc, 0)

            phases = vdata["phases"]
            self.assertGreater(len(phases), 0)

            # Verifikasi kontinuitas rentang frame
            current_frame = 0
            for p in phases:
                self.assertEqual(p["start_frame"], current_frame)
                self.assertGreaterEqual(p["end_frame"], p["start_frame"])
                current_frame = p["end_frame"] + 1

            # Pastikan frame terakhir mencapai total_frames - 1
            self.assertEqual(phases[-1]["end_frame"], total_fc - 1)

            # Pastikan fase Leap ada dan valid
            leap_phases = [p for p in phases if p.get("is_leap")]
            self.assertGreater(len(leap_phases), 0)
            for lp in leap_phases:
                self.assertIn(lp["phase"], ("leap_windup", "leap_airborne", "leap_landing"))

    def test_extracted_manifest_phases_and_label_integrity(self) -> None:
        """Memastikan manifest hasil ekstraksi memisahkan fase Leap dari pre-idle / recovery."""
        if not self.manifest_file.exists():
            self.skipTest("Manifest extracted belum di-generate.")

        with open(self.manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest["schema_version"], 2)
        self.assertGreater(manifest["total_frames_extracted"], 0)
        self.assertGreater(manifest["positive_leap_frames"], 0)
        self.assertGreater(manifest["negative_action_frames"], 0)

        # Verifikasi distribusi fase
        dist = manifest.get("leap_phases_distribution", {})
        self.assertIn("leap_airborne", dist)
        self.assertIn("leap_windup", dist)
        self.assertIn("leap_landing", dist)
        self.assertIn("idle_pre_leap", dist)

        # Pastikan tidak ada frame idle yang salah dilabeli positive_leap
        for f in manifest["frames"]:
            if f["phase"] in ("idle_pre_leap", "recovery_post_leap", "mark_pre_combo"):
                self.assertEqual(f["label"], "negative_action")
            elif f["phase"] in ("leap_windup", "leap_airborne", "leap_landing"):
                self.assertEqual(f["label"], "positive_leap")


if __name__ == "__main__":
    unittest.main()
