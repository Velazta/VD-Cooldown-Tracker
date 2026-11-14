"""Unit Tests for tools/validate_temporal.py.

Violence District Cooldown Tracker — Detector Rebuild (Phase 1)
"""

import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_temporal import validate_temporal_data, validate_temporal_file


class TestValidateTemporal(unittest.TestCase):
    """Test suite untuk validasi skema temporal annotations."""

    def test_valid_temporal_data(self) -> None:
        """Memastikan data valid lolos tanpa error."""
        valid_data = {
            "schema_version": 1,
            "killer_id": "the_hidden",
            "videos": {
                "test_vid.mp4": {
                    "fps": 30.0,
                    "total_frames": 100,
                    "duration_seconds": 3.33,
                    "events": [
                        {
                            "ability": "leap",
                            "cast_start_frame": 25,
                            "outcome": "completed"
                        }
                    ],
                    "phases": [
                        {"phase": "idle", "start_frame": 0, "end_frame": 24},
                        {"phase": "leap_windup", "start_frame": 25, "end_frame": 50}
                    ]
                }
            }
        }
        is_valid, errors = validate_temporal_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_invalid_killer_id(self) -> None:
        """Memastikan killer_id yang salah ditolak."""
        bad_data = {
            "schema_version": 1,
            "killer_id": "killer_veil",
            "videos": {"v.mp4": {"fps": 30, "total_frames": 10, "events": []}}
        }
        is_valid, errors = validate_temporal_data(bad_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("killer_id" in e for e in errors))

    def test_out_of_bounds_cast_frame(self) -> None:
        """Memastikan cast_start_frame yang melebihi total_frames ditolak."""
        bad_data = {
            "schema_version": 1,
            "killer_id": "the_hidden",
            "videos": {
                "v.mp4": {
                    "fps": 30.0,
                    "total_frames": 50,
                    "events": [
                        {
                            "ability": "leap",
                            "cast_start_frame": 150,  # di luar 50
                            "outcome": "completed"
                        }
                    ]
                }
            }
        }
        is_valid, errors = validate_temporal_data(bad_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("cast_start_frame" in e for e in errors))

    def test_invalid_ability_name(self) -> None:
        """Memastikan nama skill di luar leap/mark ditolak."""
        bad_data = {
            "schema_version": 1,
            "killer_id": "the_hidden",
            "videos": {
                "v.mp4": {
                    "fps": 30.0,
                    "total_frames": 50,
                    "events": [
                        {
                            "ability": "teleport",  # bukan leap/mark
                            "cast_start_frame": 10,
                            "outcome": "completed"
                        }
                    ]
                }
            }
        }
        is_valid, errors = validate_temporal_data(bad_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("ability" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
