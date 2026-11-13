"""Hybrid Multi-Modal Detector for The Hidden Leap.

Violence District Cooldown Tracker — Week 3 (Day 17)
Fuses Multi-Scale Template Matching, Kinematic Parabolic Motion, and Audio Cues
to maximize Leap detection precision and suppress false positives.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from detection.detection_result import DetectionResult
from detection.motion_detector import MotionDetector, MotionDetectionResult
from detection.template_detector import TemplateDetector, TemplateMatchResult


@dataclass
class HybridDetectionEvaluation:
    is_detected: bool
    confidence: float
    template_score: float
    motion_span_px: float
    fusion_strategy: str
    latency_ms: float
    detection_result: Optional[DetectionResult] = None
    target_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    matched_template: str = ""


class HybridDetector:
    """Detektor fusi multi-modal yang menggabungkan kemiripan visual dan trajektori kinematik."""

    def __init__(
        self,
        templates_dir: Path = Path("dataset/templates/the_hidden"),
        template_threshold: float = 0.54,
        min_motion_span_px: float = 80.0,
        debounce_sec: float = 15.0,
    ) -> None:
        self.template_detector = TemplateDetector(
            templates_dir=templates_dir,
            confidence_threshold=template_threshold,
            scales=(0.5, 0.75, 1.0),
            processing_downscale=0.4,
            target_phases=("leap_airborne", "leap_windup"),
        )
        self.motion_detector = MotionDetector(
            min_vertical_span_px=min_motion_span_px,
            cooldown_debounce_sec=debounce_sec,
        )
        self.debounce_sec = debounce_sec
        self.last_detection_time: float = -100.0

    def reset(self) -> None:
        """Mereset state detektor."""
        self.motion_detector.reset()
        self.last_detection_time = -100.0

    def process_frame(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
        audio_confirmed: bool = False,
    ) -> HybridDetectionEvaluation:
        """Mengevaluasi satu frame melalui pipeline visual dan kinematika."""
        tmpl_res = self.template_detector.match_frame(frame)
        return self.process_frame_with_cached_match(
            tmpl_res=tmpl_res,
            frame=frame,
            frame_index=frame_index,
            timestamp=timestamp,
            audio_confirmed=audio_confirmed,
        )

    def process_frame_with_cached_match(
        self,
        tmpl_res: TemplateMatchResult,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
        audio_confirmed: bool = False,
    ) -> HybridDetectionEvaluation:
        """Mengevaluasi satu frame dengan hasil template matching yang sudah di-cache untuk efisiensi."""
        t_start = time.perf_counter()

        # Evaluasi Kinematika Gerak
        motion_res = self.motion_detector.process_frame(frame, frame_index, timestamp)

        # 3. Logika Fusi & Validasi Multi-Modal
        is_leap = False
        strategy = "NONE"
        final_conf = 0.0

        is_debounced = (timestamp - self.last_detection_time) > self.debounce_sec

        # Strategi A: Konfirmasi Audio Kuat + Korelasi Visual Wajar (Paling Akurat / Zero FP)
        if audio_confirmed and tmpl_res.confidence >= 0.40 and is_debounced:
            is_leap = True
            strategy = "AUDIO_VISION_FUSION"
            final_conf = max(0.85, min(1.0, tmpl_res.confidence + 0.20))

        # Strategi B: Pose Melayang di Udara (Airborne) + Lonjakan Kinematika Parabolik Terkonfirmasi
        elif tmpl_res.is_detected and motion_res.is_leap_motion and is_debounced:
            is_leap = True
            strategy = "AIRBORNE_MOTION_FUSION"
            final_conf = min(1.0, (tmpl_res.confidence * 0.5) + (motion_res.confidence * 0.5))

        # Strategi C: Korelasi Visual Multi-Scale Kuat (>= 0.58)
        elif tmpl_res.is_detected and tmpl_res.confidence >= 0.58 and is_debounced:
            is_leap = True
            strategy = "MULTI_SCALE_VISION_MATCH"
            final_conf = tmpl_res.confidence

        det_result: Optional[DetectionResult] = None
        if is_leap:
            self.last_detection_time = timestamp
            det_result = DetectionResult(
                killer_id="the_hidden",
                ability_id="leap",
                event_type="cast_start",
                timestamp=timestamp,
                confidence=final_conf,
                source="hybrid" if "FUSION" in strategy else "vision",
                evidence={
                    "strategy": strategy,
                    "template_score": tmpl_res.confidence,
                    "matched_template": tmpl_res.matched_template,
                    "motion_span_px": motion_res.vertical_span_px,
                    "audio_confirmed": audio_confirmed,
                },
            )

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return HybridDetectionEvaluation(
            is_detected=is_leap,
            confidence=round(final_conf, 3),
            template_score=tmpl_res.confidence,
            motion_span_px=motion_res.vertical_span_px,
            fusion_strategy=strategy,
            latency_ms=round(t_elapsed, 2),
            detection_result=det_result,
            target_bbox=tmpl_res.best_bbox,
            matched_template=tmpl_res.matched_template,
        )
