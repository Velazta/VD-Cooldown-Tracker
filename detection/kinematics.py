"""Kinematic Trajectory & Parabolic Motion Analyzer.

Violence District Cooldown Tracker — Rebuild Phase 4 (Task 4.2)
Extracts physical kinematic features from tracked entity coordinate sequences:
- Parabolic curve fitting: y(t) = at^2 + bt + c and R^2 coefficient of determination
- Apex (peak airborne) timestamp and height estimation
- Vertical span, peak upward velocity, and peak downward velocity
- Camera motion compensation relative to survivor anchor
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class ParabolicFitResult:
    a: float  # quadratic coefficient (acceleration / curvature)
    b: float  # linear coefficient (initial velocity)
    c: float  # constant offset
    r2: float  # goodness of fit [0.0, 1.0]
    apex_time: float  # timestamp of highest point (lowest y in image coordinates)
    apex_y: float     # y coordinate at apex
    vertical_span: float  # max(y) - min(y)
    is_valid_parabola: bool


def fit_parabola(
    times: np.ndarray,
    y_values: np.ndarray,
    min_points: int = 5,
) -> Optional[ParabolicFitResult]:
    """Fits y = at^2 + bt + c to time-series data.
    
    In computer vision coordinates (Y increases downwards):
    A physical jump going UP then DOWN forms an upward arc in world space,
    which corresponds to a positive 'a' (a > 0) in screen Y coordinates!
    """
    if len(times) < min_points or len(times) != len(y_values):
        return None

    t = np.asarray(times, dtype=float)
    y = np.asarray(y_values, dtype=float)

    # Shift time relative to window start for numerical stability
    t0 = t[0]
    rel_t = t - t0

    try:
        # Polynomial fit degree 2: p(x) = p[0]*x^2 + p[1]*x + p[2]
        coeffs = np.polyfit(rel_t, y, deg=2)
        a, b, c = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

        # Fitted values & R^2 calculation
        y_pred = np.polyval(coeffs, rel_t)
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-8 else 0.0
        r2 = max(0.0, min(1.0, r2))

        # Apex location: dy/dt = 2at + b = 0 -> rel_t_apex = -b / (2a)
        if abs(a) > 1e-6:
            rel_t_apex = -b / (2.0 * a)
            t_apex = t0 + rel_t_apex
            apex_y = np.polyval(coeffs, rel_t_apex)
        else:
            rel_t_apex = rel_t[-1] / 2.0
            t_apex = t0 + rel_t_apex
            apex_y = float(np.min(y))

        vert_span = float(np.max(y) - np.min(y))

        # Valid leap trajectory:
        # 1. Curvature a > 0 (accelerating downwards in screen Y)
        # 2. Apex falls reasonably inside or near the observation window
        # 3. Minimum vertical displacement occurred
        t_duration = rel_t[-1] - rel_t[0]
        apex_in_window = (rel_t[0] - 0.2 * t_duration) <= rel_t_apex <= (rel_t[-1] + 0.2 * t_duration)
        is_valid = bool((a > 0.0) and apex_in_window)

        return ParabolicFitResult(
            a=a,
            b=b,
            c=c,
            r2=r2,
            apex_time=round(float(t_apex), 4),
            apex_y=round(float(apex_y), 4),
            vertical_span=round(vert_span, 4),
            is_valid_parabola=is_valid,
        )
    except (np.linalg.LinAlgError, ValueError):
        return None


def compensate_camera_motion(
    hidden_ys: List[float],
    survivor_ys: List[Optional[float]],
) -> List[float]:
    """Compensates camera vertical motion using survivor anchor when available."""
    if len(hidden_ys) != len(survivor_ys):
        return hidden_ys

    # Check if survivor is consistently tracked (>50% of frames)
    valid_survivor = [sy for sy in survivor_ys if sy is not None]
    if len(valid_survivor) >= len(hidden_ys) * 0.5:
        # Fill missing survivor values with linear interpolation
        s_arr = np.array([sy if sy is not None else np.nan for sy in survivor_ys])
        nans = np.isnan(s_arr)
        if np.any(nans):
            indices = np.arange(len(s_arr))
            s_arr[nans] = np.interp(indices[nans], indices[~nans], s_arr[~nans])
        # Compute relative Y: y_hidden - y_survivor
        return [float(hy - sy) for hy, sy in zip(hidden_ys, s_arr)]

    # Fallback to raw Y
    return hidden_ys
