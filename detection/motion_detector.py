"""Kinematic Parabolic Motion Detector for The Hidden Leap.

Violence District Cooldown Tracker — Week 3 (Day 17)
Tracks vertical displacement and velocity across sliding frame windows to detect
the characteristic parabolic surge of Leap and filter out horizontal weapon slashes.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple

import cv2
import numpy as np

from detection.detection_result import DetectionResult


@dataclass
class MotionFrameSample:
    frame_index: int
    timestamp: float
    centroid_y: float
    centroid_x: float
    contour_area: float


@dataclass
class MotionDetectionResult:
    is_leap_motion: bool
    confidence: float
    vertical_span_px: float
    peak_velocity_px_s: float
    state: str  # 'IDLE', 'RISING', 'FALLING', 'LEAP_CONFIRMED'
    latency_ms: float


class MotionDetector:
    """Detektor kinematika gerak berbasis foreground tracking dan state machine lintasan parabolik."""

    def __init__(
        self,
        history_window: int = 15,
        min_vertical_span_px: float = 80.0,
        min_velocity_threshold: float = 300.0,  # px/s
        cooldown_debounce_sec: float = 1.5,
    ) -> None:
        self.history_window = history_window
        self.min_vertical_span_px = min_vertical_span_px
        self.min_velocity_threshold = min_velocity_threshold
        self.cooldown_debounce_sec = cooldown_debounce_sec

        self.fgbg = cv2.createBackgroundSubtractorMOG2(history=30, varThreshold=25, detectShadows=False)
        self.history: Deque[MotionFrameSample] = collections.deque(maxlen=history_window)
        self.last_trigger_time: float = -100.0
        self.state: str = "IDLE"

    def reset(self) -> None:
        """Mereset state machine dan buffer riwayat pergerakan."""
        self.history.clear()
        self.fgbg = cv2.createBackgroundSubtractorMOG2(history=30, varThreshold=25, detectShadows=False)
        self.state = "IDLE"

    def process_frame(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
    ) -> MotionDetectionResult:
        """Memproses satu frame untuk melacak pergerakan vertikal Killer.

        Args:
            frame: Matriks citra BGR atau grayscale.
            frame_index: Indeks frame berurutan.
            timestamp: Waktu relatif atau absolut dalam detik.
        """
        t_start = time.perf_counter()

        if frame is None or frame.size == 0:
            return MotionDetectionResult(
                is_leap_motion=False,
                confidence=0.0,
                vertical_span_px=0.0,
                peak_velocity_px_s=0.0,
                state=self.state,
                latency_ms=0.0,
            )

        h, w = frame.shape[:2]
        fgmask = self.fgbg.apply(frame)

        # Bersihkan noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        dilated = cv2.dilate(cleaned, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_cnts = [
            c for c in contours
            if 1500 <= cv2.contourArea(c) <= (w * h * 0.50)
        ]

        if valid_cnts:
            largest = max(valid_cnts, key=cv2.contourArea)
            bx, by, bw, bh = cv2.boundingRect(largest)
            cx = float(bx + bw / 2.0)
            cy = float(by + bh / 2.0)
            area = float(cv2.contourArea(largest))

            self.history.append(
                MotionFrameSample(
                    frame_index=frame_index,
                    timestamp=timestamp,
                    centroid_y=cy,
                    centroid_x=cx,
                    contour_area=area,
                )
            )

        # Analisis riwayat dalam sliding window
        is_leap = False
        conf = 0.0
        v_span = 0.0
        peak_vel = 0.0

        if len(self.history) >= 4:
            cy_vals = [s.centroid_y for s in self.history]
            t_vals = [s.timestamp for s in self.history]
            v_span = float(max(cy_vals) - min(cy_vals))

            # Hitung kecepatan instan
            velocities = []
            for i in range(1, len(cy_vals)):
                dt = t_vals[i] - t_vals[i - 1]
                if dt > 0:
                    velocities.append((cy_vals[i] - cy_vals[i - 1]) / dt)

            if velocities:
                peak_vel = float(max(abs(v) for v in velocities))

            # Evaluasi pola parabolik vertikal
            has_rapid_velocity = peak_vel >= self.min_velocity_threshold
            has_span = v_span >= self.min_vertical_span_px

            # Cek debounce
            is_debounced = (timestamp - self.last_trigger_time) > self.cooldown_debounce_sec

            if has_span and has_rapid_velocity and is_debounced:
                is_leap = True
                self.state = "LEAP_CONFIRMED"
                self.last_trigger_time = timestamp
                conf = min(1.0, 0.50 + (v_span / (self.min_vertical_span_px * 2.0)) * 0.50)
            else:
                self.state = "TRACKING" if len(self.history) > 0 else "IDLE"

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return MotionDetectionResult(
            is_leap_motion=is_leap,
            confidence=round(conf, 3),
            vertical_span_px=round(v_span, 1),
            peak_velocity_px_s=round(peak_vel, 1),
            state=self.state,
            latency_ms=round(t_elapsed, 2),
        )
