"""Unit Tests for HardwareProfiler Module.

Violence District Cooldown Tracker — Week 4 (Day 22)
Verifies:
- Hardware resource sampling and psutil telemetry retrieval.
- Accurate statistical calculation (mean, median, p95, max, min).
- Short profiling run (2s) execution and PRD threshold compliance.
- Markdown report generation.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.hardware_profiler import HardwareMetricSummary, HardwareProfiler

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestHardwareProfiler(unittest.TestCase):
    """Test suite untuk HardwareProfiler."""

    def setUp(self) -> None:
        self.profiler = HardwareProfiler()

    def test_get_system_info(self) -> None:
        """Memastikan sistem info mendeteksi OS, CPU cores, dan total RAM."""
        info = self.profiler._get_system_info()
        self.assertIn("os", info)
        self.assertIn("cpu_cores_logical", info)
        self.assertGreater(info["cpu_cores_logical"], 0)
        self.assertIn("total_ram_gb", info)
        self.assertGreater(info["total_ram_gb"], 0.0)

    def test_calculate_summary(self) -> None:
        """Memastikan ringkasan statistik dihitung akurat."""
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        summary = self.profiler._calculate_summary(vals)

        self.assertIsInstance(summary, HardwareMetricSummary)
        self.assertEqual(summary.mean, 3.0)
        self.assertEqual(summary.median, 3.0)
        self.assertEqual(summary.min_val, 1.0)
        self.assertEqual(summary.max_val, 5.0)

    def test_run_short_profile_session(self) -> None:
        """Menjalankan sesi profiling singkat (2.5 detik) dan memastikan kepatuhan ambang batas."""
        res = self.profiler.run_profile_session(duration_sec=2.5, target_fps=30.0)

        self.assertGreaterEqual(res.total_frames_processed, 40)
        self.assertGreaterEqual(len(res.samples), 2)
        # RAM harus di bawah ambang batas aman (toleransi shared test runner 500 MB)
        self.assertTrue(res.target_ram_met)
        self.assertLess(res.ram_rss.max_val, 500.0)

    def test_generate_report_output(self) -> None:
        """Memverifikasi berkas laporan audit markdown berhasil dihasilkan."""
        res = self.profiler.run_profile_session(duration_sec=1.5, target_fps=30.0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_hardware_audit.md"
            content = self.profiler.generate_report(res, out_file)

            self.assertTrue(out_file.exists())
            self.assertIn("# Hardware Resource Profiling & Game FPS Impact Audit", content)
            self.assertIn("Penggunaan CPU Aplikasi", content)
            self.assertIn("Konsumsi Memori RAM", content)


if __name__ == "__main__":
    unittest.main()
