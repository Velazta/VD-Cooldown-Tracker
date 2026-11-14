"""Unit tests for HiddenTracker (detection/hidden_tracker.py)."""

import pytest
from detection.hidden_tracker import HiddenTracker, DetectionBox


def test_tracker_cold_start_and_smooth_tracking():
    tracker = HiddenTracker(max_hold_frames=5)
    assert tracker.is_active is False

    # Frame 1: Detection arrives
    det1 = [DetectionBox(class_id=0, xc=0.5, yc=0.5, w=0.1, h=0.2, confidence=0.9)]
    st1 = tracker.update(det1, frame_idx=1, timestamp=0.033)
    assert st1 is not None
    assert tracker.is_active is True
    assert st1.is_holding is False
    assert pytest.approx(st1.xc, 0.01) == 0.5
    assert pytest.approx(st1.yc, 0.01) == 0.5

    # Frame 2: Moves slightly right
    det2 = [DetectionBox(class_id=0, xc=0.52, yc=0.5, w=0.1, h=0.2, confidence=0.88)]
    st2 = tracker.update(det2, frame_idx=2, timestamp=0.066)
    assert st2 is not None
    assert st2.xc > 0.50
    assert tracker.is_active is True


def test_tracker_coasting_across_dropout_frames():
    tracker = HiddenTracker(max_hold_frames=3)

    # Initial frames moving right at 0.02 units/frame
    tracker.update([DetectionBox(0, 0.40, 0.50, 0.1, 0.2, 0.9)], 1, 0.033)
    tracker.update([DetectionBox(0, 0.42, 0.50, 0.1, 0.2, 0.9)], 2, 0.066)

    # Missing frames: 3, 4 (2 frames dropout)
    st3 = tracker.update([], frame_idx=3, timestamp=0.099)
    assert st3 is not None
    assert st3.is_holding is True
    assert tracker.is_active is True
    assert st3.xc > 0.42  # Coasted forward

    st4 = tracker.update([], frame_idx=4, timestamp=0.132)
    assert st4 is not None
    assert st4.is_holding is True

    # Frame 5: Re-detection resumes normal tracking
    st5 = tracker.update([DetectionBox(0, 0.48, 0.50, 0.1, 0.2, 0.85)], 5, 0.165)
    assert st5 is not None
    assert st5.is_holding is False
    assert tracker.is_active is True


def test_tracker_terminates_after_max_hold_exceeded():
    tracker = HiddenTracker(max_hold_frames=2)
    tracker.update([DetectionBox(0, 0.5, 0.5, 0.1, 0.2, 0.9)], 1, 0.033)

    # Hold frame 1 & 2
    assert tracker.update([], 2, 0.066) is not None
    assert tracker.update([], 3, 0.099) is not None

    # Exceeded max hold frames -> terminates
    st_term = tracker.update([], 4, 0.132)
    assert st_term is None
    assert tracker.is_active is False


def test_survivor_relative_coordinates():
    tracker = HiddenTracker()
    dets = [
        DetectionBox(class_id=0, xc=0.7, yc=0.4, w=0.1, h=0.2, confidence=0.9),  # Hidden
        DetectionBox(class_id=1, xc=0.5, yc=0.5, w=0.2, h=0.4, confidence=0.95), # Survivor anchor
    ]

    st = tracker.update(dets, frame_idx=1, timestamp=0.033)
    assert st is not None
    assert st.rel_x_to_survivor is not None
    assert pytest.approx(st.rel_x_to_survivor, 0.01) == 0.20  # 0.7 - 0.5
    assert pytest.approx(st.rel_y_to_survivor, 0.01) == -0.10 # 0.4 - 0.5
