"""Unit Tests for tools/make_splits.py.

Violence District Cooldown Tracker — Detector Rebuild (Phase 1)
"""

import unittest
from tools.make_splits import create_video_splits, verify_no_leakage


class TestMakeSplits(unittest.TestCase):
    """Test suite untuk video-level splitting tanpa data leakage."""

    def test_verify_no_leakage_clean(self) -> None:
        """Memastikan split tanpa overlap lolos verifikasi."""
        splits = {
            "train": ["v1.mp4", "v2.mp4", "v3.mp4"],
            "val": ["v4.mp4"],
            "test": ["v5.mp4", "v6.mp4"],
        }
        is_clean, errs = verify_no_leakage(splits)
        self.assertTrue(is_clean)
        self.assertEqual(len(errs), 0)

    def test_verify_no_leakage_dirty(self) -> None:
        """Memastikan split dengan overlap terdeteksi sebagai leakage error."""
        dirty_splits = {
            "train": ["v1.mp4", "v2.mp4"],
            "val": ["v2.mp4", "v3.mp4"],  # v2 bocor ke val
            "test": ["v4.mp4"],
        }
        is_clean, errs = verify_no_leakage(dirty_splits)
        self.assertFalse(is_clean)
        self.assertGreater(len(errs), 0)
        self.assertTrue("v2.mp4" in errs[0])

    def test_create_video_splits_unseen_skin(self) -> None:
        """Memastikan unseen skin prefix selalu diarahkan ke Test split."""
        dummy_videos = [
            {"file_name": "hidden1_leap.mp4", "category": "leap_action", "is_positive_leap": True},
            {"file_name": "hidden1_mark.mp4", "category": "mark_action", "is_positive_leap": False},
            {"file_name": "hidden1_chase.mp4", "category": "chasing", "is_positive_leap": False},
            {"file_name": "hidden2_leap.mp4", "category": "leap_action", "is_positive_leap": True},
            {"file_name": "hidden2_mark.mp4", "category": "mark_action", "is_positive_leap": False},
            {"file_name": "hidden3_unseen_leap.mp4", "category": "leap_action", "is_positive_leap": True},
            {"file_name": "hidden3_unseen_neg.mp4", "category": "chasing", "is_positive_leap": False},
        ]

        splits_data = create_video_splits(dummy_videos, test_skin_prefixes=["hidden3_"])
        splits = splits_data["splits"]

        # Pastikan hidden3 hanya ada di test
        self.assertIn("hidden3_unseen_leap.mp4", splits["test"])
        self.assertIn("hidden3_unseen_neg.mp4", splits["test"])
        self.assertNotIn("hidden3_unseen_leap.mp4", splits["train"])
        self.assertNotIn("hidden3_unseen_leap.mp4", splits["val"])

        # Verifikasi zero leakage
        is_clean, errs = verify_no_leakage(splits)
        self.assertTrue(is_clean)


if __name__ == "__main__":
    unittest.main()
