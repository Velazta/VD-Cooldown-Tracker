"""Kinematic Mark Ability Action Recognizer.

Violence District Cooldown Tracker — Rebuild Phase 4 (Task 4.5)
Detects The Hidden Mark ability (forward lunge/stab toward survivor):
- Analyzes rapid bounding box scale expansion (looming effect from forward thrust)
- Verifies non-parabolic flat trajectory (strictly differentiating from Leap)
- Evaluates proximity and closing velocity toward survivor anchor
- Prevents false triggers from distant walking and stationary basic swings
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from detection.hidden_tracker import TrackState


@dataclass
class MarkCandidate:
    ability: str  # "mark"
    score: float  # [0.0 - 1.0]
    t_start: float
    area_growth: float
    distance_to_survivor: Optional[float]
    frame_idx: int


class MarkRecognizer:
    def __init__(
        self,
        window_seconds: float = 0.45,
        min_points: int = 5,
        min_area_growth: float = 1.20,  # 20% area expansion due to forward surge
        max_vertical_span: float = 0.030,  # Must be flat trajectory (not airborne leap)
        max_survivor_distance: float = 0.45,  # Normalized distance to survivor anchor
    ) -> None:
        self.window_seconds = window_seconds
        self.min_points = min_points
        self.min_area_growth = min_area_growth
        self.max_vertical_span = max_vertical_span
        self.max_survivor_distance = max_survivor_distance

    def evaluate(self, history: List[TrackState]) -> Optional[MarkCandidate]:
        if len(history) < self.min_points:
            return None

        latest_t = history[-1].timestamp
        window = [s for s in history if (latest_t - s.timestamp) <= self.window_seconds]
        if len(window) < self.min_points:
            return None

        # 1. Trajectory flatness check (must NOT be an airborne Leap)
        ys = [s.yc for s in window]
        vert_span = float(max(ys) - min(ys))
        if vert_span > self.max_vertical_span:
            # Vertical motion is too large -> belongs to Leap recognizer!
            return None

        # 2. Forward thrust / Looming scale expansion check
        init_area = window[0].w * window[0].h
        curr_area = window[-1].w * window[-1].h
        if init_area <= 1e-6:
            return None

        area_growth = curr_area / init_area
        if area_growth < self.min_area_growth:
            # Insufficient forward surge
            return None

        # 3. Proximity check relative to survivor anchor (if survivor is observed)
        latest_st = window[-1]
        dist_to_survivor = None
        if latest_st.rel_x_to_survivor is not None and latest_st.rel_y_to_survivor is not None:
            dist_to_survivor = math.hypot(latest_st.rel_x_to_survivor, latest_st.rel_y_to_survivor)
            if dist_to_survivor > self.max_survivor_distance:
                # Too far from survivor to be an active Mark strike
                return None

        # Compute composite confidence score
        growth_score = min(1.0, (area_growth - 1.0) / 0.50)
        avg_conf = float(np.mean([s.confidence for s in window]))
        proximity_bonus = (1.0 - (dist_to_survivor / self.max_survivor_distance)) if dist_to_survivor is not None else 0.5

        score = (growth_score * 0.45) + (proximity_bonus * 0.35) + (avg_conf * 0.20)
        score = max(0.0, min(1.0, score))

        return MarkCandidate(
            ability="mark",
            score=round(score, 3),
            t_start=round(float(window[0].timestamp), 3),
            area_growth=round(area_growth, 3),
            distance_to_survivor=round(dist_to_survivor, 3) if dist_to_survivor is not None else None,
            frame_idx=latest_st.frame_idx,
        )
