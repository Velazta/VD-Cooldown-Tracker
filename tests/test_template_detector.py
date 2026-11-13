"""Unit Tests for TemplateDetector Module.

Violence District Cooldown Tracker — Week 3 (Day 17)
Verifies:
- Template loading from dataset/templates/the_hidden
- Multi-scale template matching execution and latency
- Bounding box scaling and projection
- DetectionResult emission on positive leap templates
"""

from __future__ import annotations

import time
from pathlib import Path
import unittest

import numpy as np

from detection.template_detector import TemplateDetector, TemplateMatchResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestTemplateDetector(unittest.TestCase):
    """Test suite untuk TemplateDetector."""

    def setUp(self) -> None:
        self.templates_dir = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"
        self.detector = TemplateDetector(templates_dir=self.templates_dir)

    def test_load_templates_success(self) -> None:
        """Memastikan template acuan berhasil dimuat."""
        count = self.detector.load_templates()
        self.assertGreaterEqual(count, 4)

    def test_match_frame_synthetic(self) -> None:
        """Memverifikasi matching pada citra sintetis menghasilkan skor dan latensi terukur."""
        # Frame kosong abu-abu
        frame = np.full((720, 1280, 3), 128, dtype=np.uint8)
        # Warmup pass
        self.detector.match_frame(frame)
        result = self.detector.match_frame(frame)

        self.assertIsInstance(result, TemplateMatchResult)
        self.assertGreaterEqual(result.latency_ms, 0.0)
        self.assertLess(result.latency_ms, 200.0)  # Toleransi real-time under test load

    def test_detect_emits_result_on_threshold(self) -> None:
        """Memastikan detect menghasilkan DetectionResult jika template cocok melampaui threshold."""
        # Buat frame sintetis yang memuat template acuan persis di dalamnya
        if self.detector.loaded_templates:
            sample_tmpl = self.detector.loaded_templates[0]
            tw, th = sample_tmpl["width"], sample_tmpl["height"]
            frame = np.full((720, 1280), 50, dtype=np.uint8)
            # Tempel template di tengah frame
            frame[200 : 200 + th, 300 : 300 + tw] = sample_tmpl["image"]

            detector_high_sens = TemplateDetector(
                templates_dir=self.templates_dir,
                confidence_threshold=0.40,
                processing_downscale=1.0,  # Skala penuh untuk perfect synthetic match
                target_phases=(sample_tmpl["phase"],),
            )
            det = detector_high_sens.detect(frame, timestamp=123.45)
            self.assertIsNotNone(det)
            if det:
                self.assertEqual(det.killer_id, "the_hidden")
                self.assertEqual(det.ability_id, "leap")
                self.assertEqual(det.timestamp, 123.45)


if __name__ == "__main__":
    unittest.main()
