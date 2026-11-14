"""Unit tests for LeapRecognizer (detection/leap_recognizer.py)."""

import numpy as np
import pytest

from detection.hidden_tracker import TrackState
from detection.leap_recognizer import LeapRecognizer


def create_synthetic_trajectory(
    duration: float = 0.6,
    num_points: int = 18,
    is_leap: bool = True,
    current_progress: float = 1.0,  # 1.0 = completed flight; 0.2 = early windup
) -> list[TrackState]:
    total_t = np.linspace(0.0, duration, num_points)
    points_to_include = max(5, int(round(num_points * current_progress)))
    times = total_t[:points_to_include]

    states = []
    for idx, t in enumerate(times):
        if is_leap:
            # Parabolic trajectory: apex at t=0.3s (y = 4.0*(t - 0.3)^2 + 0.3)
            # Y starts at 0.66, reaches apex (lowest screen Y) at 0.30, lands back at 0.66
            yc = float(4.0 * (t - 0.3) ** 2 + 0.30)
            xc = float(0.40 + 0.20 * (t / duration))
        else:
            # Walking / chasing flat motion
            yc = float(0.50 + 0.005 * np.sin(t * 10))
            xc = float(0.30 + 0.10 * (t / duration))

        st = TrackState(
            timestamp=round(float(t), 4),
            frame_idx=idx,
            xc=xc,
            yc=yc,
            w=0.08,
            h=0.15,
            vx=0.1,
            vy=0.1,
            confidence=0.90,
            is_holding=False,
            rel_x_to_survivor=xc - 0.50,
            rel_y_to_survivor=yc - 0.65,  # Survivor is standing at y=0.65
        )
        states.append(st)
    return states


def test_recognize_airborne_leap_success():
    recognizer = LeapRecognizer(min_points=6, min_r2=0.50, require_airborne_apex=True)
    # Full flight through apex
    history = create_synthetic_trajectory(duration=0.6, num_points=20, is_leap=True, current_progress=1.0)

    candidate = recognizer.evaluate(history)
    assert candidate is not None
    assert candidate.ability == "leap"
    assert candidate.score > 0.6
    assert candidate.r2 > 0.8
    assert pytest.approx(candidate.apex_time, 0.05) == 0.30


def test_reject_premature_windup_before_airborne():
    recognizer = LeapRecognizer(min_points=5, min_r2=0.50, require_airborne_apex=True)
    # Only early windup (first 25% of jump, before apex)
    history = create_synthetic_trajectory(duration=0.6, num_points=20, is_leap=True, current_progress=0.25)

    candidate = recognizer.evaluate(history)
    # Must NOT trigger during early ancang-ancang!
    assert candidate is None


def test_reject_flat_walking_chase():
    recognizer = LeapRecognizer(min_points=6, min_r2=0.50)
    history = create_synthetic_trajectory(duration=0.6, num_points=20, is_leap=False, current_progress=1.0)

    candidate = recognizer.evaluate(history)
    assert candidate is None
