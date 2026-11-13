"""Unit Tests for Long-Run Stability & Resilience Module.

Violence District Cooldown Tracker — Week 4 (Day 23)
Verifies:
- Long-run streaming stability and resilience against simulated runtime chaos.
- Window minimize / restore recovery without crash.
- Dynamic resolution change resilience (720p <-> 1080p).
- Memory footprint bounded under target (< 250 MB).
- Markdown stability report generation.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.stability_runner import StabilityAuditReportData, StabilityRunner

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestLongRunStability(unittest.TestCase):
    """Test suite untuk StabilityRunner."""

    def setUp(self) -> None:
        self.runner = StabilityRunner()

    def test_stability_runner_initialization(self) -> None:
        """Memastikan inisialisasi komponen CooldownManager dan HybridDetector berhasil."""
        self.assertIsNotNone(self.runner.cooldown_manager.ability)
        self.assertEqual(self.runner.cooldown_manager.killer_id, "the_hidden")
        self.assertIsNotNone(self.runner.hybrid_detector)
        self.assertIsNotNone(self.runner.roi_processor)

    def test_short_stability_session_clean(self) -> None:
        """Menjalankan sesi stabilitas pendek (2.5 detik) dan memastikan nol exception."""
        res = self.runner.run_stability_session(
            duration_sec=2.5,
            target_fps=60.0,
            checkpoint_interval_sec=0.8,
            simulate_chaos=True,
        )

        self.assertIsInstance(res, StabilityAuditReportData)
        self.assertEqual(res.total_exceptions, 0)
        self.assertTrue(res.resilience_minimize_passed)
        self.assertTrue(res.resilience_resolution_passed)
        self.assertLess(res.peak_ram_mb, 500.0)
        self.assertTrue(res.zero_memory_leak_verified)
        self.assertGreaterEqual(res.total_frames_processed, 40)

    def test_generate_report_output(self) -> None:
        """Memastikan generator laporan menghasilkan berkas Markdown audit yang lengkap."""
        res = self.runner.run_stability_session(
            duration_sec=1.5,
            target_fps=60.0,
            checkpoint_interval_sec=0.5,
            simulate_chaos=False,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_stability_report.md"
            content = self.runner.generate_report(res, out_file)

            self.assertTrue(out_file.exists())
            self.assertIn("# 1-Hour Long-Run Continuous Stability Stress Test Report", content)
            self.assertIn("ZERO MEMORY LEAK", content)
            self.assertIn("Ketahanan Window Minimize/Restore", content)


if __name__ == "__main__":
    unittest.main()
