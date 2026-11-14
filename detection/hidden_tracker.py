"""Spatial-Temporal Entity Tracker for The Hidden & Survivor Reference.

Violence District Cooldown Tracker — Rebuild Phase 4 (Task 4.1)
Tracks The Hidden across frames with:
- Centroid & IoU association
- Exponential Moving Average (EMA) coordinate smoothing
- N-frame coasting/hold during brief occlusion or detector dropout
- Survivor anchor tracking for camera motion compensation
- Velocity vector calculation (vx, vy)
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple


@dataclass
class DetectionBox:
    class_id: int  # 0: hidden, 1: survivor
    xc: float      # normalized 0.0 - 1.0
    yc: float      # normalized 0.0 - 1.0
    w: float       # normalized 0.0 - 1.0
    h: float       # normalized 0.0 - 1.0
    confidence: float


@dataclass
class TrackState:
    timestamp: float
    frame_idx: int
    xc: float
    yc: float
    w: float
    h: float
    vx: float  # normalized units per second
    vy: float  # normalized units per second
    confidence: float
    is_holding: bool
    rel_x_to_survivor: Optional[float] = None
    rel_y_to_survivor: Optional[float] = None


def compute_iou_norm(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
    xc1, yc1, w1, h1 = b1
    xc2, yc2, w2, h2 = b2
    x1_min, y1_min = xc1 - w1 / 2.0, yc1 - h1 / 2.0
    x1_max, y1_max = xc1 + w1 / 2.0, yc1 + h1 / 2.0
    x2_min, y2_min = xc2 - w2 / 2.0, yc2 - h2 / 2.0
    x2_max, y2_max = xc2 + w2 / 2.0, yc2 + h2 / 2.0

    inter_w = max(0.0, min(x1_max, x2_max) - max(x1_min, x2_min))
    inter_h = max(0.0, min(y1_max, y2_max) - max(y1_min, y2_min))
    inter = inter_w * inter_h
    union = (w1 * h1) + (w2 * h2) - inter
    return inter / union if union > 0 else 0.0


class HiddenTracker:
    def __init__(
        self,
        max_hold_frames: int = 6,
        max_history_len: int = 120,
        ema_alpha: float = 0.65,
        max_association_dist: float = 0.20,
    ) -> None:
        self.max_hold_frames = max_hold_frames
        self.max_history_len = max_history_len
        self.ema_alpha = ema_alpha
        self.max_association_dist = max_association_dist

        self.history: Deque[TrackState] = collections.deque(maxlen=max_history_len)
        self.lost_frames: int = 0
        self.is_active: bool = False

        # Current state
        self.curr_xc: float = 0.0
        self.curr_yc: float = 0.0
        self.curr_w: float = 0.0
        self.curr_h: float = 0.0
        self.curr_vx: float = 0.0
        self.curr_vy: float = 0.0

        # Survivor anchor state
        self.survivor_anchor: Optional[Tuple[float, float, float, float]] = None

    def reset(self) -> None:
        self.history.clear()
        self.lost_frames = 0
        self.is_active = False
        self.survivor_anchor = None
        self.curr_xc = 0.0
        self.curr_yc = 0.0
        self.curr_w = 0.0
        self.curr_h = 0.0
        self.curr_vx = 0.0
        self.curr_vy = 0.0

    def update(
        self,
        detections: List[DetectionBox],
        frame_idx: int,
        timestamp: float,
    ) -> Optional[TrackState]:
        # 1. Update survivor anchor (highest confidence survivor detection)
        survivor_candidates = [d for d in detections if d.class_id == 1]
        if survivor_candidates:
            best_s = max(survivor_candidates, key=lambda s: s.confidence)
            self.survivor_anchor = (best_s.xc, best_s.yc, best_s.w, best_s.h)

        # 2. Extract Hidden candidates (class_id == 0)
        hidden_candidates = [d for d in detections if d.class_id == 0]
        matched_candidate: Optional[DetectionBox] = None

        if not self.is_active:
            # Cold start: pick highest confidence Hidden
            if hidden_candidates:
                matched_candidate = max(hidden_candidates, key=lambda d: d.confidence)
                self.curr_xc = matched_candidate.xc
                self.curr_yc = matched_candidate.yc
                self.curr_w = matched_candidate.w
                self.curr_h = matched_candidate.h
                self.curr_vx = 0.0
                self.curr_vy = 0.0
                self.lost_frames = 0
                self.is_active = True
        else:
            # Active track: associate with nearest candidate via centroid distance / IoU
            best_score = -1.0
            for cand in hidden_candidates:
                dist = math.hypot(cand.xc - self.curr_xc, cand.yc - self.curr_yc)
                iou = compute_iou_norm(
                    (self.curr_xc, self.curr_yc, self.curr_w, self.curr_h),
                    (cand.xc, cand.yc, cand.w, cand.h),
                )
                if dist <= self.max_association_dist:
                    # Score combines IoU, proximity, and confidence
                    score = (1.0 - (dist / self.max_association_dist)) * 0.5 + iou * 0.3 + cand.confidence * 0.2
                    if score > best_score:
                        best_score = score
                        matched_candidate = cand

        dt = 1.0 / 30.0  # default delta time fallback
        if self.history:
            prev_t = self.history[-1].timestamp
            if timestamp > prev_t:
                dt = timestamp - prev_t

        if matched_candidate is not None:
            # Update position with EMA smoothing
            raw_vx = (matched_candidate.xc - self.curr_xc) / dt if dt > 0 else 0.0
            raw_vy = (matched_candidate.yc - self.curr_yc) / dt if dt > 0 else 0.0

            self.curr_vx = self.ema_alpha * raw_vx + (1.0 - self.ema_alpha) * self.curr_vx
            self.curr_vy = self.ema_alpha * raw_vy + (1.0 - self.ema_alpha) * self.curr_vy

            self.curr_xc = self.ema_alpha * matched_candidate.xc + (1.0 - self.ema_alpha) * self.curr_xc
            self.curr_yc = self.ema_alpha * matched_candidate.yc + (1.0 - self.ema_alpha) * self.curr_yc
            self.curr_w = self.ema_alpha * matched_candidate.w + (1.0 - self.ema_alpha) * self.curr_w
            self.curr_h = self.ema_alpha * matched_candidate.h + (1.0 - self.ema_alpha) * self.curr_h

            self.lost_frames = 0
            is_holding = False
            conf = matched_candidate.confidence
        else:
            # Missing detection: coast / hold with last known velocity
            self.lost_frames += 1
            if self.lost_frames <= self.max_hold_frames:
                self.curr_xc += self.curr_vx * dt
                self.curr_yc += self.curr_vy * dt
                is_holding = True
                conf = max(0.1, 0.5 - (0.05 * self.lost_frames))
            else:
                self.is_active = False
                return None

        # Compute relative coordinate to survivor if anchor exists
        rel_x, rel_y = None, None
        if self.survivor_anchor is not None:
            rel_x = self.curr_xc - self.survivor_anchor[0]
            rel_y = self.curr_yc - self.survivor_anchor[1]

        state = TrackState(
            timestamp=round(timestamp, 4),
            frame_idx=frame_idx,
            xc=self.curr_xc,
            yc=self.curr_yc,
            w=self.curr_w,
            h=self.curr_h,
            vx=self.curr_vx,
            vy=self.curr_vy,
            confidence=conf,
            is_holding=is_holding,
            rel_x_to_survivor=rel_x,
            rel_y_to_survivor=rel_y,
        )
        self.history.append(state)
        return state

    def get_history(self, window_seconds: Optional[float] = None) -> List[TrackState]:
        if not self.history:
            return []
        if window_seconds is None:
            return list(self.history)
        latest_t = self.history[-1].timestamp
        return [s for s in self.history if (latest_t - s.timestamp) <= window_seconds]
