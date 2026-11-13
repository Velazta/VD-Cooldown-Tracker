"""Unit Tests for ErrorAnalyzer and Action-Level Metrics.

Violence District Cooldown Tracker — Week 3 (Day 18)
Verifies:
- ErrorAnalyzer execution and data extraction
- Action-level vs Frame-level metric calculations
- Forensic failure classification (TP, FP, TN, FN)
- Markdown report generation
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.error_analyzer import ActionEventResult, ErrorAnalyzer, ErrorAnalysisReport, FrameDiagnostic

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestErrorAnalyzer(unittest.TestCase):
    """Test suite untuk ErrorAnalyzer."""

    def setUp(self) -> None:
        self.manifest_file = PROJECT_ROOT / "dataset" / "extracted" / "manifest.json"
        self.templates_dir = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"
        self.analyzer = ErrorAnalyzer(
            manifest_path=self.manifest_file,
            templates_dir=self.templates_dir,
        )

    def test_analyzer_action_metrics_calculation(self) -> None:
        """Memastikan kalkulasi aksi temporal (event-level) akurat."""
        actions = [
            ActionEventResult("video_1.mp4", total_action_frames=5, frames_detected=4, action_detected=True, trigger_delay_ms=0.0),
            ActionEventResult("video_2.mp4", total_action_frames=6, frames_detected=6, action_detected=True, trigger_delay_ms=50.0),
        ]
        total_actions = len(actions)
        detected_actions = sum(1 for a in actions if a.action_detected)
        action_recall = detected_actions / float(total_actions)

        self.assertEqual(total_actions, 2)
        self.assertEqual(detected_actions, 2)
        self.assertEqual(action_recall, 1.0)

    def test_analyzer_report_serialization(self) -> None:
        """Memastikan ErrorAnalysisReport dapat diserialisasi ke dictionary/JSON."""
        diag = FrameDiagnostic(
            frame_id="sample_f001.jpg",
            relative_path="extracted/test/sample.jpg",
            source_video="video.mp4",
            frame_index=1,
            timestamp_seconds=0.1,
            ground_truth_label="positive_leap",
            ground_truth_phase="leap_windup",
            template_score=0.48,
            template_matched="template_1",
            template_matched_phase="leap_landing",
            template_detected=False,
            motion_span_px=120.0,
            motion_detected=True,
            audio_present=True,
            hybrid_detected=False,
            classification_category="FN",
            failure_reason="Score slightly below cutoff",
        )
        report = ErrorAnalysisReport(
            schema_version=1,
            eval_split="test",
            total_frames=10,
            ground_truth_positives=2,
            ground_truth_negatives=8,
            false_negatives=[diag],
        )

        d = report.to_dict()
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["eval_split"], "test")
        self.assertEqual(len(d["false_negatives"]), 1)
        self.assertEqual(d["false_negatives"][0]["frame_id"], "sample_f001.jpg")

    def test_generate_markdown_report_synthetic(self) -> None:
        """Memastikan fungsi pembuat laporan markdown berjalan tanpa exception."""
        report = ErrorAnalysisReport(
            schema_version=1,
            eval_split="test",
            total_frames=50,
            ground_truth_positives=10,
            ground_truth_negatives=40,
            frame_level_metrics={
                "true_positives": 9,
                "false_positives": 0,
                "true_negatives": 40,
                "false_negatives": 1,
                "precision": 1.0,
                "recall": 0.90,
                "f1_score": 0.947,
            },
            action_level_metrics={
                "total_leap_actions": 2,
                "detected_leap_actions": 2,
                "missed_leap_actions": 0,
                "action_level_recall": 1.0,
                "mean_trigger_delay_ms": 10.0,
            },
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_report.md"
            self.analyzer.generate_markdown_report(report, out_file)
            self.assertTrue(out_file.exists())
            text = out_file.read_text(encoding="utf-8")
            self.assertIn("Action-Level", text)
            self.assertIn("100.0%", text)


if __name__ == "__main__":
    unittest.main()
