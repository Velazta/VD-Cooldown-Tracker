"""Multi-Scale Template Matching Baseline Detector for The Hidden Leap (Optimized).

Violence District Cooldown Tracker — Week 3 (Day 17)
Performs normalized cross-correlation (cv2.TM_CCOEFF_NORMED) across pre-cached
canonical action templates with spatial pyramid downscaling.
Emits validated DetectionResult objects with latency < 25 ms.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from detection.detection_result import DetectionResult


@dataclass
class TemplateMatchDetail:
    template_id: str
    phase: str
    action_type: str
    score: float
    best_scale: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h) in original frame coordinates


@dataclass
class TemplateMatchResult:
    is_detected: bool
    confidence: float
    matched_phase: str
    matched_template: str
    best_bbox: Tuple[int, int, int, int]
    latency_ms: float
    details: List[TemplateMatchDetail] = field(default_factory=list)


class TemplateDetector:
    """Detektor visual baseline berbasis OpenCV Multi-Scale Template Matching dengan pre-cached scaling."""

    def __init__(
        self,
        templates_dir: Path = Path("dataset/templates/the_hidden"),
        scales: Tuple[float, ...] = (0.5, 0.75, 1.0),
        confidence_threshold: float = 0.54,
        processing_downscale: float = 0.4,
        target_phases: Tuple[str, ...] = ("leap_airborne", "leap_windup"),
    ) -> None:
        self.templates_dir = Path(templates_dir).resolve()
        self.scales = scales
        self.confidence_threshold = confidence_threshold
        self.processing_downscale = processing_downscale
        self.target_phases = target_phases
        self.loaded_templates: List[Dict[str, Any]] = []
        self.cached_scaled_templates: List[Dict[str, Any]] = []
        self.load_templates()

    def load_templates(self) -> int:
        """Memuat template citra grayscale dari direktori templates dan meng-cache versi berskala."""
        self.loaded_templates.clear()
        self.cached_scaled_templates.clear()

        manifest_file = self.templates_dir / "templates_manifest.json"
        if not manifest_file.exists():
            return 0

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        scale_factor = self.processing_downscale

        for tmpl_meta in manifest_data.get("templates", []):
            phase = tmpl_meta.get("phase", "")
            action_type = tmpl_meta.get("action_type", "")
            tmpl_id = tmpl_meta.get("template_id", "")

            # Prioritaskan target_phases
            if self.target_phases and phase not in self.target_phases:
                continue

            img_file = self.templates_dir / f"{tmpl_id}.png"
            if not img_file.exists():
                continue

            tmpl_mat = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
            if tmpl_mat is None:
                continue

            tmpl_h, tmpl_w = tmpl_mat.shape[:2]

            self.loaded_templates.append(
                {
                    "template_id": tmpl_id,
                    "phase": phase,
                    "action_type": action_type,
                    "image": tmpl_mat,
                    "width": tmpl_w,
                    "height": tmpl_h,
                }
            )

            # Pre-cache versi berskala agar tidak perlu cv2.resize di runtime loop
            for s in self.scales:
                scaled_tw = int(tmpl_w * s * scale_factor)
                scaled_th = int(tmpl_h * s * scale_factor)
                if scaled_tw >= 15 and scaled_th >= 15:
                    scaled_mat = cv2.resize(tmpl_mat, (scaled_tw, scaled_th))
                    self.cached_scaled_templates.append(
                        {
                            "template_id": tmpl_id,
                            "phase": phase,
                            "action_type": action_type,
                            "scale": s,
                            "scaled_width": scaled_tw,
                            "scaled_height": scaled_th,
                            "scaled_image": scaled_mat,
                        }
                    )

        return len(self.loaded_templates)

    def match_frame(self, frame: np.ndarray) -> TemplateMatchResult:
        """Mengevaluasi satu frame citra terhadap pustaka template acuan.

        Args:
            frame: Matriks citra BGR atau Grayscale (umumnya 1280x720).

        Returns:
            TemplateMatchResult berisi skor tertinggi, bounding box, dan latensi komputasi.
        """
        t_start = time.perf_counter()

        if frame is None or frame.size == 0 or not self.cached_scaled_templates:
            return TemplateMatchResult(
                is_detected=False,
                confidence=0.0,
                matched_phase="none",
                matched_template="none",
                best_bbox=(0, 0, 0, 0),
                latency_ms=0.0,
            )

        # Konversi ke Grayscale jika masih BGR
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        orig_h, orig_w = gray.shape[:2]
        scale_factor = self.processing_downscale

        # Downscale piramida untuk optimasi latensi real-time
        if scale_factor < 1.0:
            small_w = int(orig_w * scale_factor)
            small_h = int(orig_h * scale_factor)
            proc_frame = cv2.resize(gray, (small_w, small_h))
        else:
            proc_frame = gray
            scale_factor = 1.0

        best_score = -1.0
        best_phase = "none"
        best_tmpl_id = "none"
        best_bbox = (0, 0, 0, 0)
        details: List[TemplateMatchDetail] = []

        # Evaluasi terhadap template berskala yang sudah di-cache
        for item in self.cached_scaled_templates:
            phase = item["phase"]
            action_type = item["action_type"]
            tmpl_id = item["template_id"]
            s = item["scale"]
            scaled_tmpl = item["scaled_image"]
            scaled_tw = item["scaled_width"]
            scaled_th = item["scaled_height"]

            if scaled_tw >= proc_frame.shape[1] or scaled_th >= proc_frame.shape[0]:
                continue

            # Jalankan Normalized Cross-Correlation
            res = cv2.matchTemplate(proc_frame, scaled_tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            # Proyeksikan kembali koordinat bounding box ke skala asli
            orig_bx = int(max_loc[0] / scale_factor)
            orig_by = int(max_loc[1] / scale_factor)
            orig_bw = int(scaled_tw / scale_factor)
            orig_bh = int(scaled_th / scale_factor)

            score = float(np.clip(max_val, 0.0, 1.0))

            details.append(
                TemplateMatchDetail(
                    template_id=tmpl_id,
                    phase=phase,
                    action_type=action_type,
                    score=round(score, 3),
                    best_scale=s,
                    bbox=(orig_bx, orig_by, orig_bw, orig_bh),
                )
            )

            if score > best_score:
                best_score = score
                best_phase = phase
                best_tmpl_id = tmpl_id
                best_bbox = (orig_bx, orig_by, orig_bw, orig_bh)

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        final_conf = max(0.0, best_score)
        is_detected = (final_conf >= self.confidence_threshold) and (best_phase in self.target_phases)

        return TemplateMatchResult(
            is_detected=is_detected,
            confidence=round(final_conf, 3),
            matched_phase=best_phase,
            matched_template=best_tmpl_id,
            best_bbox=best_bbox,
            latency_ms=round(t_elapsed, 2),
            details=details,
        )

    def detect(
        self,
        frame: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> Optional[DetectionResult]:
        """Menjalankan matching dan menghasilkan DetectionResult jika Leap terkonfirmasi."""
        match_res = self.match_frame(frame)
        if not match_res.is_detected:
            return None

        event_time = timestamp if timestamp is not None else time.monotonic()
        event_type = "cast_start" if match_res.matched_phase in ("leap_windup", "leap_airborne") else "release"

        evidence = {
            "template_id": match_res.matched_template,
            "phase": match_res.matched_phase,
            "bbox": match_res.best_bbox,
            "latency_ms": match_res.latency_ms,
        }

        return DetectionResult(
            killer_id="the_hidden",
            ability_id="leap",
            event_type=event_type,
            timestamp=event_time,
            confidence=match_res.confidence,
            source="vision",
            evidence=evidence,
        )
