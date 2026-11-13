"""YOLOv8-Nano Neural Object Detector using ONNX Runtime.

Violence District Cooldown Tracker — Week 5 (Day 25)
Provides high-speed, lightweight neural object detection for Killer tracking.
Features:
- Aspect-ratio preserving letterbox preprocessing with FP32 normalization.
- CPU SIMD inference via ONNX Runtime (< 15-20 ms).
- Non-Maximum Suppression (NMS) decoding for precise entity bounding boxes.
- Resilient fallback / mock mode when weights file is not yet deployed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    ort = None
    HAS_ONNX = False

from app.logger import get_logger
from detection.base_detector import BaseDetector

logger = get_logger("detection.yolo")

DEFAULT_CLASSES = [
    "hidden_grounded",
    "hidden_leap_airborne",
    "hidden_mark_stab",
]


@dataclass
class YoloTargetBox:
    """Kotak pembatas objek hasil inferensi YOLO."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h) dalam koordinat citra asli
    class_id: int
    class_name: str
    confidence: float

    @property
    def centroid(self) -> Tuple[float, float]:
        """Menghitung titik tengah (cx, cy) bounding box."""
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)


@dataclass
class YoloDetectionResult:
    """Hasil evaluasi lengkap satu frame dari YoloDetector."""
    is_detected: bool
    targets: List[YoloTargetBox] = field(default_factory=list)
    best_target: Optional[YoloTargetBox] = None
    latency_ms: float = 0.0
    input_shape: Tuple[int, int] = (0, 0)


class YoloDetector(BaseDetector):
    """Detektor objek neural berbasis YOLOv8-Nano dan ONNX Runtime."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        input_size: Tuple[int, int] = (320, 320),
        confidence_threshold: float = 0.40,
        nms_threshold: float = 0.45,
        class_names: Optional[List[str]] = None,
    ) -> None:
        self.model_path = Path(model_path).resolve() if model_path else None
        self.input_size = input_size
        self._confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.class_names = class_names or DEFAULT_CLASSES

        self.session: Optional[Any] = None
        self.input_name: str = ""
        self.output_name: str = ""

        if self.model_path and self.model_path.exists() and HAS_ONNX:
            self._load_onnx_session()
        else:
            logger.info("YoloDetector initialized in mock/stub mode (model file not yet present).")

    @property
    def confidence_threshold(self) -> float:
        return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        self._confidence_threshold = max(0.10, min(0.95, value))
        logger.info("YoloDetector confidence threshold set to: %.2f", self._confidence_threshold)

    def _load_onnx_session(self) -> bool:
        """Memuat session inferensi ONNX dengan CPU Execution Provider."""
        if not HAS_ONNX or not self.model_path or not self.model_path.exists():
            return False

        try:
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.intra_op_num_threads = 2

            self.session = ort.InferenceSession(
                str(self.model_path),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            logger.info("ONNX Runtime session successfully loaded from %s", self.model_path)
            return True
        except Exception as exc:
            logger.error("Failed to load ONNX model %s: %s", self.model_path, exc)
            self.session = None
            return False

    @staticmethod
    def letterbox(
        image: np.ndarray,
        new_shape: Tuple[int, int] = (320, 320),
        color: Tuple[int, int, int] = (114, 114, 114),
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Mengubah ukuran citra dengan mempertahankan aspek rasio dan menambahkan padding.

        Returns:
            Tuple[resized_padded_image, scale_ratio, (pad_left, pad_top)]
        """
        shape = image.shape[:2]  # [height, width]
        target_h, target_w = new_shape

        # Hitung rasio penskalaan
        r = min(target_h / shape[0], target_w / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))

        # Hitung padding yang dibutuhkan
        dw = target_w - new_unpad[0]
        dh = target_h - new_unpad[1]
        dw /= 2.0
        dh /= 2.0

        if shape[::-1] != new_unpad:
            resized = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)
        else:
            resized = image.copy()

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )
        return padded, r, (int(round(dw)), int(round(dh)))

    def preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Mempersiapkan frame citra BGR ke bentuk input tensor NCHW FP32 normalized."""
        padded, ratio, (pad_w, pad_h) = self.letterbox(frame, self.input_size)
        # BGR ke RGB, normalisasi ke [0.0, 1.0]
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        # HWC ke CHW -> (1, C, H, W)
        tensor = np.transpose(rgb, (2, 0, 1))
        tensor = np.expand_dims(tensor, axis=0)
        return np.ascontiguousarray(tensor), ratio, (pad_w, pad_h)

    def decode_predictions(
        self,
        output_tensor: np.ndarray,
        orig_shape: Tuple[int, int],
        ratio: float,
        pad: Tuple[int, int],
    ) -> List[YoloTargetBox]:
        """Mendekode output tensor YOLOv8 [1, 4 + num_classes, num_anchors] dan menerapkan NMS."""
        # YOLOv8 output: shape (1, 4 + num_classes, N) -> transpose ke (N, 4 + num_classes)
        preds = np.squeeze(output_tensor)
        if preds.ndim == 2 and preds.shape[0] < preds.shape[1]:
            preds = preds.T

        pad_w, pad_h = pad
        orig_h, orig_w = orig_shape

        boxes: List[List[int]] = []
        confidences: List[float] = []
        class_ids: List[int] = []

        num_classes = len(self.class_names)

        for row in preds:
            cx, cy, w, h = row[:4]
            scores = row[4 : 4 + num_classes] if len(row) >= 4 + num_classes else [float(row[4])]
            class_id = int(np.argmax(scores))
            conf = float(scores[class_id])

            if conf >= self._confidence_threshold:
                # Konversi dari letterbox koordinat kembali ke koordinat asli
                x1 = int(round((cx - w / 2.0 - pad_w) / ratio))
                y1 = int(round((cy - h / 2.0 - pad_h) / ratio))
                box_w = int(round(w / ratio))
                box_h = int(round(h / ratio))

                # Clamping batas koordinat citra
                x1 = max(0, min(orig_w - 1, x1))
                y1 = max(0, min(orig_h - 1, y1))
                box_w = max(1, min(orig_w - x1, box_w))
                box_h = max(1, min(orig_h - y1, box_h))

                boxes.append([x1, y1, box_w, box_h])
                confidences.append(conf)
                class_ids.append(class_id)

        # Terapkan Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self._confidence_threshold, self.nms_threshold)

        results: List[YoloTargetBox] = []
        if len(indices) > 0:
            for idx in np.asarray(indices).flatten():
                bx, by, bw, bh = boxes[idx]
                cid = class_ids[idx]
                cname = self.class_names[cid] if cid < len(self.class_names) else f"class_{cid}"
                results.append(
                    YoloTargetBox(
                        bbox=(bx, by, bw, bh),
                        class_id=cid,
                        class_name=cname,
                        confidence=round(confidences[idx], 3),
                    )
                )

        return results

    def process_frame(
        self,
        frame: np.ndarray,
        frame_index: int = 0,
        timestamp: float = 0.0,
        **kwargs: Any,
    ) -> YoloDetectionResult:
        """Mengeksekusi inferensi YOLOv8-Nano penuh pada citra input."""
        t_start = time.perf_counter()

        if frame is None or frame.size == 0:
            return YoloDetectionResult(is_detected=False, latency_ms=0.0)

        orig_shape = frame.shape[:2]

        # Jika model ONNX nyata belum dimuat, jalankan jalur mock / stub
        if self.session is None:
            t_elapsed = (time.perf_counter() - t_start) * 1000.0
            return YoloDetectionResult(
                is_detected=False,
                targets=[],
                best_target=None,
                latency_ms=round(t_elapsed, 2),
                input_shape=orig_shape,
            )

        # 1. Preprocessing (Letterbox + Normalize)
        tensor, ratio, pad = self.preprocess(frame)

        # 2. Eksekusi Inferensi ONNX
        outputs = self.session.run([self.output_name], {self.input_name: tensor})

        # 3. Decoding & NMS
        targets = self.decode_predictions(outputs[0], orig_shape, ratio, pad)

        # Cari target killer dengan keyakinan tertinggi
        best_target = max(targets, key=lambda t: t.confidence) if targets else None
        is_detected = best_target is not None and best_target.confidence >= self._confidence_threshold

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return YoloDetectionResult(
            is_detected=is_detected,
            targets=targets,
            best_target=best_target,
            latency_ms=round(t_elapsed, 2),
            input_shape=orig_shape,
        )
