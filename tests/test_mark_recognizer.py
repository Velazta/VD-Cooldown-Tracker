"""Unit tests for MarkRecognizer (detection/mark_recognizer.py)."""

import pytest
from detection.hidden_tracker import TrackState
from detection.mark_recognizer import MarkRecognizer


def create_synthetic_mark_sequence(
    area_growth: float = 1.35,
    vert_span: float = 0.01,
    dist_to_survivor: float = 0.25,
) -> list[TrackState]:
    states = []
    # 8 frames over 0.26 seconds
    base_w, base_h = 0.06, 0.12
    for i in range(8):
        t = i * 0.033
        prog = i / 7.0
        # Bounding box expands as killer lunges forward
        w = base_w * (1.0 + (area_growth**0.5 - 1.0) * prog)
        h = base_h * (1.0 + (area_growth**0.5 - 1.0) * prog)
        yc = 0.50 + (vert_span * prog)

        st = TrackState(
            timestamp=round(t, 4),
            frame_idx=i,
            xc=0.45 + 0.05 * prog,
            yc=yc,
            w=w,
            h=h,
            vx=0.1,
            vy=0.01,
            confidence=0.90,
            is_holding=False,
            rel_x_to_survivor=dist_to_survivor,
            rel_y_to_survivor=0.05,
        )
        states.append(st)
    return states


def test_recognize_valid_mark_lunge():
    recognizer = MarkRecognizer(min_area_growth=1.20, max_vertical_span=0.030)
    history = create_synthetic_mark_sequence(area_growth=1.35, vert_span=0.01, dist_to_survivor=0.20)

    candidate = recognizer.evaluate(history)
    assert candidate is not None
    assert candidate.ability == "mark"
    assert candidate.score > 0.6
    assert candidate.area_growth >= 1.30


def test_reject_airborne_leap_as_mark():
    recognizer = MarkRecognizer(min_area_growth=1.20, max_vertical_span=0.030)
    # Vertical span is 0.08 (airborne leap)
    history = create_synthetic_mark_sequence(area_growth=1.35, vert_span=0.08, dist_to_survivor=0.20)

    candidate = recognizer.evaluate(history)
    # Large vertical motion must NOT be recognized as Mark!
    assert candidate is None


def test_reject_constant_size_walking():
    recognizer = MarkRecognizer(min_area_growth=1.20)
    # Area growth is 1.02 (negligible size change while walking)
    history = create_synthetic_mark_sequence(area_growth=1.02, vert_span=0.005, dist_to_survivor=0.20)

    candidate = recognizer.evaluate(history)
    assert candidate is None


def test_reject_when_too_far_from_survivor():
    recognizer = MarkRecognizer(min_area_growth=1.20, max_survivor_distance=0.40)
    # Killer is very far from survivor (distance = 0.65)
    history = create_synthetic_mark_sequence(area_growth=1.40, vert_span=0.01, dist_to_survivor=0.65)

    candidate = recognizer.evaluate(history)
    assert candidate is None
