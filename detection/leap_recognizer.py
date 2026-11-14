"""Kinematic Leap Ability Action Recognizer.

Violence District Cooldown Tracker — Rebuild Phase 4 (Task 4.3)
Detects The Hidden Leap ability during the airborne flight phase:
- Analyzes sliding temporal window of tracked positions
- Evaluates parabolic fit (y = at^2 + bt + c, downward acceleration a > 0)
- Verifies mid-air airborne state (at or crossing parabolic apex)
- Rejects walking bob, flat running, and single-frame visual flicker
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from detection.hidden_tracker import TrackState
from detection.kinematics import compensate_camera_motion, fit_parabola


@dataclass
class LeapCandidate:
    ability: str  # "leap"
    score: float  # [0.0 - 1.0]
    t_start: float
    apex_time: float
    vertical_span: float
    r2: float
    frame_idx: int


class LeapRecognizer:
    def __init__(
        self,
        window_seconds: float = 0.80,
        min_points: int = 6,
        min_r2: float = 0.50,
        min_vertical_span: float = 0.035,  # normalized screen height
        require_airborne_apex: bool = True,
    ) -> None:
        self.window_seconds = window_seconds
        self.min_points = min_points
        self.min_r2 = min_r2
        self.min_vertical_span = min_vertical_span
        self.require_airborne_apex = require_airborne_apex

    def evaluate(self, history: List[TrackState]) -> Optional[LeapCandidate]:
        """Evaluates recent track states to recognize an in-progress or completed Leap."""
        if len(history) < self.min_points:
            return None

        # Take points within window_seconds from latest state
        latest_t = history[-1].timestamp
        window = [s for s in history if (latest_t - s.timestamp) <= self.window_seconds]
        if len(window) < self.min_points:
            return None

        times = np.array([s.timestamp for s in window])
        hidden_ys = [s.yc for s in window]
        survivor_ys = [s.yc - s.rel_y_to_survivor if s.rel_y_to_survivor is not None else None for s in window]

        # Compensate for camera pitch and bounce using survivor anchor
        comp_ys = np.array(compensate_camera_motion(hidden_ys, survivor_ys))

        fit = fit_parabola(times, comp_ys, min_points=self.min_points)
        if fit is None or not fit.is_valid_parabola:
            return None

        # Verification 1: Goodness of fit (R^2 >= min_r2)
        if fit.r2 < self.min_r2:
            return None

        # Verification 2: Meaningful vertical span (avoid micro-jitters)
        if fit.vertical_span < self.min_vertical_span:
            return None

        # Verification 3: Mid-air airborne check
        # The Hidden must be in flight (apex reached or within 100ms of apex)
        if self.require_airborne_apex:
            # If current time is earlier than apex - 0.15s, killer is still in early windup on ground!
            if latest_t < (fit.apex_time - 0.15):
                return None

        # Compute composite confidence score
        avg_conf = float(np.mean([s.confidence for s in window]))
        score = (fit.r2 * 0.45) + (min(1.0, fit.vertical_span / 0.10) * 0.35) + (avg_conf * 0.20)
        score = max(0.0, min(1.0, score))

        t_start = float(times[0])
        return LeapCandidate(
            ability="leap",
            score=round(score, 3),
            t_start=round(t_start, 3),
            apex_time=fit.apex_time,
            vertical_span=fit.vertical_span,
            r2=round(fit.r2, 3),
            frame_idx=window[-1].frame_idx,
        )
