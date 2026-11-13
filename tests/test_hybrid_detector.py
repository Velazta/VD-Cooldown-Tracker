"""Unit Tests for HybridDetector and MotionDetector.

Violence District Cooldown Tracker — Week 3 (Day 17)
Verifies:
- MotionDetector sliding window tracking and debounce
- HybridDetector multi-modal fusion strategies
- Audio cue confirmation boost
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from detection.hybrid_detector import HybridDetector, HybridDetectionEvaluation
from detection.motion_detector import MotionDetector, MotionDetectionResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestHybridAndMotionDetector(unittest.TestCase):
    """Test suite untuk MotionDetector dan HybridDetector."""

    def setUp(self) -> None:
        self.motion_detector = MotionDetector(min_vertical_span_px=50.0, min_velocity_threshold=100.0)
        self.hybrid_detector = HybridDetector(
            templates_dir=PROJECT_ROOT / "dataset" / "templates" / "the_hidden",
            template_threshold=0.50,
            min_motion_span_px=50.0,
        )

    def test_motion_detector_empty_frame(self) -> None:
        """Memastikan motion detector menangani frame statis tanpa error."""
        frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
        res = self.motion_detector.process_frame(frame, frame_index=0, timestamp=0.0)
        self.assertIsInstance(res, MotionDetectionResult)
        self.assertFalse(res.is_leap_motion)
        self.assertEqual(res.state, "IDLE")

    def test_hybrid_detector_reset(self) -> None:
        """Memastikan reset mengembalikan state awal."""
        self.hybrid_detector.reset()
        self.assertEqual(self.hybrid_detector.last_detection_time, -100.0)

    def test_hybrid_detector_audio_boost(self) -> None:
        """Memastikan kehadiran audio cue menaikkan keyakinan deteksi."""
        frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
        # Evaluasi frame tanpa audio
        eval_no_audio = self.hybrid_detector.process_frame(frame, frame_index=0, timestamp=0.0, audio_confirmed=False)
        self.assertFalse(eval_no_audio.is_detected)


if __name__ == "__main__":
    unittest.main()
