"""Unit Tests for YoloDetector Module.

Violence District Cooldown Tracker — Week 5 (Day 25)
Verifies:
- YoloTargetBox centroid calculation and data structures.
- Letterbox preprocessing (padding, aspect ratio, bounds).
- Preprocessing tensor output (NCHW shape, FP32, normalization).
- Prediction decoding and NMS bounding box extraction.
- Safe execution in mock/stub mode.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import cv2
import numpy as np

from detection.yolo_detector import YoloDetectionResult, YoloDetector, YoloTargetBox

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestYoloDetector(unittest.TestCase):
    """Test suite untuk YoloDetector dan komponen neural ONNX."""

    def setUp(self) -> None:
        self.detector = YoloDetector(
            input_size=(320, 320),
            confidence_threshold=0.40,
            nms_threshold=0.45,
            class_names=["killer_the_hidden", "killer_veil", "survivor"],
        )

    def test_target_box_centroid(self) -> None:
        """Memverifikasi kalkulasi centroid (cx, cy) dari YoloTargetBox."""
        box = YoloTargetBox(
            bbox=(100, 200, 50, 80),
            class_id=0,
            class_name="killer_the_hidden",
            confidence=0.85,
        )
        cx, cy = box.centroid
        self.assertEqual(cx, 125.0)
        self.assertEqual(cy, 240.0)

    def test_letterbox_preprocessing(self) -> None:
        """Memastikan letterbox menghasilkan citra target 320x320 dengan padding simetris."""
        # Frame input 1280x720 (16:9)
        frame = np.full((720, 1280, 3), 50, dtype=np.uint8)
        padded, ratio, (pad_w, pad_h) = self.detector.letterbox(frame, (320, 320))

        self.assertEqual(padded.shape, (320, 320, 3))
        self.assertAlmostEqual(ratio, 320 / 1280, places=3)
        self.assertEqual(pad_w, 0)
        self.assertGreater(pad_h, 0)

    def test_preprocess_tensor_contract(self) -> None:
        """Memverifikasi tensor keluaran preprocess berformat NCHW FP32 normalized."""
        frame = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        tensor, ratio, pad = self.detector.preprocess(frame)

        self.assertEqual(tensor.shape, (1, 3, 320, 320))
        self.assertEqual(tensor.dtype, np.float32)
        self.assertGreaterEqual(tensor.min(), 0.0)
        self.assertLessEqual(tensor.max(), 1.0)

    def test_decode_predictions_synthetic(self) -> None:
        """Memverifikasi decoding tensor prediksi YOLOv8 [1, 4+C, N] dan penerapan NMS."""
        # 1 anchor buatan dengan skor The Hidden tinggi di tengah frame
        num_classes = 3
        num_anchors = 100
        # Format [1, 4 + C, N]
        preds = np.zeros((1, 4 + num_classes, num_anchors), dtype=np.float32)

        # Anchor ke-10: cx=160, cy=160, w=40, h=80 (dalam koordinat letterbox 320x320)
        preds[0, 0, 10] = 160.0
        preds[0, 1, 10] = 160.0
        preds[0, 2, 10] = 40.0
        preds[0, 3, 10] = 80.0
        preds[0, 4, 10] = 0.90  # Skor kelas 0: killer_the_hidden = 90%

        boxes = self.detector.decode_predictions(
            output_tensor=preds,
            orig_shape=(720, 1280),
            ratio=0.25,
            pad=(0, 70),
        )

        self.assertGreaterEqual(len(boxes), 1)
        best = boxes[0]
        self.assertEqual(best.class_id, 0)
        self.assertEqual(best.class_name, "killer_the_hidden")
        self.assertAlmostEqual(best.confidence, 0.90, places=2)
        self.assertGreater(best.bbox[2], 0)
        self.assertGreater(best.bbox[3], 0)

    def test_process_frame_empty_or_mock(self) -> None:
        """Memastikan process_frame mengembalikan YoloDetectionResult aman tanpa error saat mock."""
        res_empty = self.detector.process_frame(None)
        self.assertIsInstance(res_empty, YoloDetectionResult)
        self.assertFalse(res_empty.is_detected)

        # Mock frame run
        frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
        res_mock = self.detector.process_frame(frame)
        self.assertIsInstance(res_mock, YoloDetectionResult)
        self.assertFalse(res_mock.is_detected)
        self.assertGreaterEqual(res_mock.latency_ms, 0.0)

    def test_confidence_threshold_clamping(self) -> None:
        """Memverifikasi batas penjepitan confidence threshold [0.10, 0.95]."""
        self.detector.confidence_threshold = 0.05
        self.assertEqual(self.detector.confidence_threshold, 0.10)

        self.detector.confidence_threshold = 0.99
        self.assertEqual(self.detector.confidence_threshold, 0.95)


if __name__ == "__main__":
    unittest.main()
