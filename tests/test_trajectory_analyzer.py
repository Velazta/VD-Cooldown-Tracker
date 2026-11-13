"""Unit and Integration Tests for Kinematic Trajectory Analyzer.

Violence District Cooldown Tracker — Week 3 (Day 16)
Verifies:
- Centroid tracking and velocity calculation (Vy, Ay)
- Parabolic curve fitting and R^2 determination
- Kinematic signature distinction between Leap vs linear attacks
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.trajectory_analyzer import TrajectoryAnalyzer, ActionTrajectoryProfile, TrajectoryAnalysisReport

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestTrajectoryAnalyzer(unittest.TestCase):
    """Test suite untuk TrajectoryAnalyzer."""

    def setUp(self) -> None:
        self.report_file = PROJECT_ROOT / "dataset" / "trajectory_profiles.json"
        self.analyzer = TrajectoryAnalyzer()

    def test_trajectory_report_validity(self) -> None:
        """Memastikan laporan profil trajektori kinematika valid dan mendeteksi signature Leap."""
        self.assertTrue(self.report_file.exists())
        with open(self.report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["total_sequences_analyzed"], 18)
        self.assertGreaterEqual(data["leap_sequences_detected"], 4)

        # Verifikasi profil Leap memiliki span vertikal signifikan
        profiles = data["profiles"]
        leap_profiles = [p for p in profiles if p["is_parabolic_leap_signature"]]
        self.assertGreaterEqual(len(leap_profiles), 4)

        for lp in leap_profiles:
            self.assertEqual(lp["action_type"], "leap_action")
            self.assertGreaterEqual(lp["vertical_span_pixels"], 60.0)
            self.assertGreaterEqual(lp["parabolic_fit_r2"], 0.50)
            # Velocity puncak lompatan ke atas harus bernilai negatif (koordinat piksel)
            self.assertLess(lp["peak_upward_velocity"], 0.0)

    def test_basic_attacks_not_parabolic_leap(self) -> None:
        """Memastikan serangan tebasan pisau biasa (basic attack) tidak keliru diklasifikasikan sebagai parabolic leap."""
        with open(self.report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        attack_profiles = [p for p in data["profiles"] if p["action_type"] == "basic_attack"]
        for ap in attack_profiles:
            self.assertFalse(ap["is_parabolic_leap_signature"])


if __name__ == "__main__":
    unittest.main()
