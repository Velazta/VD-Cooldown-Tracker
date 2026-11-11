"""
Normalized Template Matching Engine (TM_CCOEFF_NORMED)
Violence District Cooldown Tracker
"""
import time
from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import numpy as np


@dataclass
class MatchResult:
    """Hasil pencocokan pola visual."""
    confidence: float                     # Skor kemiripan (0.0 s/d 1.0)
    matched_location: Tuple[int, int]     # (top_left_x, top_left_y)
    matched_rect: Tuple[int, int, int, int] # (x, y, width, height)
    match_time_ms: float                  # Waktu komputasi matching (ms)


class TemplateMatcher:
    """
    Engine pencocokan template berbasis Normalized Cross-Correlation (TM_CCOEFF_NORMED).
    Digunakan sebagai baseline detektor pola visual (PRD Bab 6.2).
    """

    def __init__(self, method: int = cv2.TM_CCOEFF_NORMED, default_threshold: float = 0.80):
        self.method = method
        self.default_threshold = default_threshold

    def match(
        self,
        image: np.ndarray,
        template: np.ndarray,
        threshold: Optional[float] = None
    ) -> Optional[MatchResult]:
        """
        Mencari posisi template di dalam gambar sumber.
        Mengembalikan MatchResult jika confidence >= threshold, atau None jika di bawah threshold.
        """
        if image is None or template is None:
            return None
        if image.size == 0 or template.size == 0:
            return None

        thresh = self.default_threshold if threshold is None else threshold

        # 1. Validasi Dimensi (Template tidak boleh lebih besar dari gambar sumber)
        img_h, img_w = image.shape[:2]
        tpl_h, tpl_w = template.shape[:2]
        if tpl_w > img_w or tpl_h > img_h:
            return None

        t0 = time.perf_counter()

        # 2. Sinkronisasi Channel Warna (Grayscale jika salah satu satu-channel)
        proc_img = image
        proc_tpl = template

        img_is_gray = len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1)
        tpl_is_gray = len(template.shape) == 2 or (len(template.shape) == 3 and template.shape[2] == 1)

        if img_is_gray != tpl_is_gray:
            if not img_is_gray:
                proc_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if not tpl_is_gray:
                proc_tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Mencegah division-by-zero pada TM_CCOEFF_NORMED jika template adalah warna polos (zero variance)
        if float(np.std(proc_tpl)) < 1e-4:
            return None

        # 3. Eksekusi Template Matching
        match_map = cv2.matchTemplate(proc_img, proc_tpl, self.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_map)

        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0

        # Untuk TM_CCOEFF_NORMED, nilai terbaik adalah max_val (rentang -1.0 s/d 1.0)
        confidence = max(0.0, float(max_val))

        if confidence >= thresh:
            best_x, best_y = max_loc
            return MatchResult(
                confidence=round(confidence, 4),
                matched_location=(best_x, best_y),
                matched_rect=(best_x, best_y, tpl_w, tpl_h),
                match_time_ms=elapsed_ms
            )

        return None

    def draw_match(
        self,
        image: np.ndarray,
        result: MatchResult,
        color: Tuple[int, int, int] = (0, 255, 255),
        thickness: int = 2
    ) -> np.ndarray:
        """Menggambar bounding box penanda kecocokan pada citra sumber."""
        if image is None or result is None:
            return image

        annotated = image.copy()
        x, y, w, h = result.matched_rect
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, thickness)
        label = f"Match: {result.confidence * 100:.1f}% ({result.match_time_ms:.1f}ms)"
        cv2.putText(
            annotated,
            label,
            (x, max(15, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA
        )
        return annotated
