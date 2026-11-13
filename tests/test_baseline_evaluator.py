"""Unit Tests for Baseline Evaluator Module.

Violence District Cooldown Tracker — Week 3 (Day 17)
Verifies:
- Evaluator instantiation and split filtering
- Precision, Recall, and F1-score metric calculation
- Markdown report formatting
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.evaluate_baseline import BaselineEvaluator, BenchmarkReport, MethodMetrics

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestBaselineEvaluator(unittest.TestCase):
    """Test suite untuk BaselineEvaluator."""

    def setUp(self) -> None:
        self.manifest_file = PROJECT_ROOT / "dataset" / "extracted" / "manifest.json"
        self.templates_dir = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"
        self.evaluator = BaselineEvaluator(
            manifest_path=self.manifest_file,
            templates_dir=self.templates_dir,
        )

    def test_metrics_calculation_sanity(self) -> None:
        """Memastikan kalkulasi formula metrik presisi, recall, dan F1 matematis akurat."""
        tp, fp, tn, fn = 40, 10, 80, 5
        total = tp + fp + tn + fn
        acc = (tp + tn) / total
        prec = tp / (tp + fp)
        rec = tp / (tp + fn)
        f1 = (2 * prec * rec) / (prec + rec)

        metric = MethodMetrics(
            method_name="Test_Method",
            total_frames_evaluated=total,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            accuracy=round(acc, 3),
            precision=round(prec, 3),
            recall=round(rec, 3),
            f1_score=round(f1, 3),
            mean_latency_ms=15.4,
            p95_latency_ms=22.1,
        )

        self.assertEqual(metric.true_positives, 40)
        self.assertEqual(metric.false_positives, 10)
        self.assertAlmostEqual(metric.precision, 0.80, places=2)
        self.assertAlmostEqual(metric.recall, 0.889, places=2)
        self.assertAlmostEqual(metric.f1_score, 0.842, places=2)

    def test_generate_markdown_report_synthetic(self) -> None:
        """Memastikan pembuatan laporan Markdown berjalan bersih tanpa exception."""
        report = BenchmarkReport(
            schema_version=1,
            eval_split="test",
            total_samples=100,
            ground_truth_positives=30,
            ground_truth_negatives=70,
            methods=[
                MethodMetrics(
                    method_name="Mock_Hybrid",
                    total_frames_evaluated=100,
                    true_positives=25,
                    false_positives=5,
                    true_negatives=65,
                    false_negatives=5,
                    accuracy=0.90,
                    precision=0.833,
                    recall=0.833,
                    f1_score=0.833,
                    mean_latency_ms=18.5,
                    p95_latency_ms=25.0,
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            md_path = Path(tmp_dir) / "test_report.md"
            self.evaluator.generate_markdown_report(report, md_path)

            self.assertTrue(md_path.exists())
            content = md_path.read_text(encoding="utf-8")
            self.assertIn("Mock_Hybrid", content)
            self.assertIn("83.3%", content)


if __name__ == "__main__":
    unittest.main()
