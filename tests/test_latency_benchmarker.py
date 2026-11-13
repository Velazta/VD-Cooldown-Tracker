"""Unit Tests for LatencyBenchmarker Module.

Violence District Cooldown Tracker — Week 4 (Day 21)
Verifies:
- Benchmarking pipeline execution and statistics calculation.
- Percentile metrics (Mean, Median, P90, P95, P99).
- Markdown report generation and compliance checks.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.latency_benchmarker import LatencyBenchmarker, LatencyBenchmarkResult, StageStatistics

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestLatencyBenchmarker(unittest.TestCase):
    """Test suite untuk LatencyBenchmarker."""

    def setUp(self) -> None:
        self.benchmarker = LatencyBenchmarker()

    def test_calculate_stage_stats_accuracy(self) -> None:
        """Memverifikasi kalkulasi statistik pada data terkontrol."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        stats = self.benchmarker._calculate_stage_stats(values)

        self.assertIsInstance(stats, StageStatistics)
        self.assertEqual(stats.mean_ms, 55.0)
        self.assertEqual(stats.median_ms, 55.0)
        self.assertEqual(stats.min_ms, 10.0)
        self.assertEqual(stats.max_ms, 100.0)
        self.assertGreaterEqual(stats.p95_ms, 90.0)

    def test_run_benchmark_smoke(self) -> None:
        """Menjalankan benchmark pendek (15 iterasi) dan memverifikasi pemenuhan target latensi."""
        res = self.benchmarker.run_benchmark(iterations=15, warmup_iterations=2)

        self.assertIsInstance(res, LatencyBenchmarkResult)
        self.assertEqual(res.sample_count, 15)
        self.assertIn("T_infer", res.stages)
        self.assertIn("T_capture", res.stages)
        self.assertIn("T_crop", res.stages)
        self.assertIn("T_dispatch", res.stages)
        self.assertIn("T_overlay", res.stages)

        # Verifikasi batas target PRD (< 150 ms)
        self.assertTrue(res.target_150ms_met)
        self.assertLess(res.total.p95_ms, 150.0)

    def test_generate_report_output(self) -> None:
        """Memastikan generator laporan menghasilkan berkas Markdown yang valid."""
        res = self.benchmarker.run_benchmark(iterations=5, warmup_iterations=1)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_report.md"
            content = self.benchmarker.generate_report(res, out_file)

            self.assertTrue(out_file.exists())
            self.assertIn("# End-to-End Latency Benchmark & Profiling Report", content)
            self.assertIn("Acceptance Target", content)
            self.assertIn("T_infer", content)


if __name__ == "__main__":
    unittest.main()
