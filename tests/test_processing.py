"""
Unit Tests for Image Preprocessing & Template Matcher
Violence District Cooldown Tracker
"""
import unittest
import numpy as np
import cv2

from processing.preprocessing import ImagePreprocessor, PreprocessingConfig, PreprocessorMode
from processing.template_matcher import TemplateMatcher, MatchResult


class TestImagePreprocessor(unittest.TestCase):
    """Pengujian Unit untuk Filter Preprocessing OpenCV."""

    def setUp(self):
        # Buat frame dummy 3-channel BGR 400x300
        self.frame = np.full((300, 400, 3), 40, dtype=np.uint8)  # Background gelap
        # Tambahkan objek terang di tengah
        cv2.circle(self.frame, (200, 150), 40, (200, 200, 200), -1)

    def test_raw_mode(self):
        preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.RAW))
        res, t = preprocessor.process(self.frame)
        self.assertEqual(res.shape, (300, 400, 3))
        self.assertGreaterEqual(t, 0.0)

    def test_grayscale_mode(self):
        preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.GRAYSCALE))
        res, t = preprocessor.process(self.frame)
        self.assertEqual(len(res.shape), 2)
        self.assertEqual(res.shape, (300, 400))

    def test_clahe_contrast_enhancement(self):
        preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.CLAHE))
        res, t = preprocessor.process(self.frame)
        self.assertEqual(res.shape, (300, 400, 3))
        # CLAHE harus meningkatkan brightness lokal pada scene gelap
        self.assertGreater(np.mean(res), np.mean(self.frame))

    def test_threshold_mode(self):
        preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.THRESHOLD, threshold_val=100))
        res, t = preprocessor.process(self.frame)
        self.assertEqual(len(res.shape), 2)
        unique_vals = set(np.unique(res))
        # Hanya boleh ada nilai biner 0 dan 255
        self.assertTrue(unique_vals.issubset({0, 255}))

    def test_canny_edge_mode(self):
        preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.CANNY))
        res, t = preprocessor.process(self.frame)
        self.assertEqual(len(res.shape), 2)
        # Deteksi tepi lingkaran harus menghasilkan pixel tepi > 0
        self.assertGreater(np.count_nonzero(res), 50)

    def test_scale_factor(self):
        preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.RAW, scale_factor=0.5))
        res, t = preprocessor.process(self.frame)
        self.assertEqual(res.shape, (150, 200, 3))


class TestTemplateMatcher(unittest.TestCase):
    """Pengujian Unit untuk Normalized Cross-Correlation Template Matcher."""

    def setUp(self):
        # Buat scene 400x300 dengan lingkaran di (180, 130) s/d (220, 170)
        self.scene = np.zeros((300, 400, 3), dtype=np.uint8)
        cv2.circle(self.scene, (200, 150), 30, (0, 255, 255), -1)

        # Template tepat berupa potongan lingkaran tersebut
        self.template = self.scene[120:180, 170:230].copy()

    def test_exact_template_match(self):
        matcher = TemplateMatcher(default_threshold=0.85)
        res = matcher.match(self.scene, self.template)

        self.assertIsNotNone(res)
        self.assertIsInstance(res, MatchResult)
        # Confidence pada potongan identik harus mendekati 1.0
        self.assertGreaterEqual(res.confidence, 0.95)
        self.assertEqual(res.matched_location, (170, 120))

    def test_negative_template_match(self):
        # Template berupa pola garis silang berbeda yang tidak ada di scene
        negative_template = np.zeros((60, 60, 3), dtype=np.uint8)
        cv2.line(negative_template, (0, 0), (60, 60), (255, 0, 0), 4)
        cv2.line(negative_template, (0, 60), (60, 0), (255, 0, 0), 4)

        matcher = TemplateMatcher(default_threshold=0.85)
        res = matcher.match(self.scene, negative_template)
        self.assertIsNone(res)

    def test_flat_zero_variance_template_handling(self):
        """Memastikan template warna polos (zero variance) ditolak secara aman."""
        flat_template = np.full((30, 30, 3), 128, dtype=np.uint8)
        matcher = TemplateMatcher()
        res = matcher.match(self.scene, flat_template)
        self.assertIsNone(res)

    def test_oversized_template_handling(self):
        """Memastikan template yang lebih besar dari frame tidak memicu crash."""
        oversized = np.zeros((400, 500, 3), dtype=np.uint8)
        matcher = TemplateMatcher()
        res = matcher.match(self.scene, oversized)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
