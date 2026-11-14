"""Unit tests for EventValidator (detection/event_validator.py)."""

from pathlib import Path
import pytest

from detection.event_validator import (
    SingleAbilityValidator,
    AbilityValidatorConfig,
    EventValidator,
    ValidatorState,
)
from detection.leap_recognizer import LeapCandidate


def make_dummy_leap(score: float = 0.85) -> LeapCandidate:
    return LeapCandidate(
        ability="leap",
        score=score,
        t_start=1.0,
        apex_time=1.3,
        vertical_span=0.08,
        r2=0.92,
        frame_idx=10,
    )


def test_validator_normal_n_of_m_confirmation(tmp_path: Path):
    cfg = AbilityValidatorConfig(
        ability_id="leap",
        cooldown_seconds=10.0,
        min_track_age_frames=4,
        required_votes_n=3,
        window_frames_m=5,
        min_score=0.60,
    )
    val = SingleAbilityValidator(cfg, log_file=tmp_path / "test_log.jsonl")

    # Frame 1: Candidate 1 (Votes: 1/1 -> State CANDIDATE)
    ev1 = val.process_frame(make_dummy_leap(), track_age=5, timestamp=1.0, frame_idx=1)
    assert ev1 is None
    assert val.state == ValidatorState.CANDIDATE

    # Frame 2: Candidate 2 (Votes: 2/2 -> State CANDIDATE)
    ev2 = val.process_frame(make_dummy_leap(), track_age=6, timestamp=1.033, frame_idx=2)
    assert ev2 is None
    assert val.state == ValidatorState.CANDIDATE

    # Frame 3: Candidate 3 (Votes: 3/3 -> CONFIRMED!)
    ev3 = val.process_frame(make_dummy_leap(), track_age=7, timestamp=1.066, frame_idx=3)
    assert ev3 is not None
    assert ev3.ability_id == "leap"
    assert ev3.source == "vision"
    assert ev3.confidence > 0.80
    assert val.state == ValidatorState.REFRACTORY


def test_validator_refractory_lockout_and_expiration(tmp_path: Path):
    cfg = AbilityValidatorConfig(ability_id="leap", cooldown_seconds=5.0, required_votes_n=1, window_frames_m=1)
    val = SingleAbilityValidator(cfg, log_file=tmp_path / "test_log.jsonl")

    # Trigger action at t=10.0
    ev = val.process_frame(make_dummy_leap(), track_age=5, timestamp=10.0, frame_idx=1)
    assert ev is not None
    assert val.state == ValidatorState.REFRACTORY

    # During cooldown (t=12.0): candidates must be ignored
    ev_locked = val.process_frame(make_dummy_leap(), track_age=5, timestamp=12.0, frame_idx=2)
    assert ev_locked is None
    assert val.state == ValidatorState.REFRACTORY

    # After cooldown expires (t=15.1): returns to IDLE and can trigger again
    ev_new = val.process_frame(make_dummy_leap(), track_age=5, timestamp=15.1, frame_idx=3)
    assert ev_new is not None
    assert ev_new.ability_id == "leap"


def test_validator_rejects_premature_track_spikes(tmp_path: Path):
    cfg = AbilityValidatorConfig(ability_id="leap", cooldown_seconds=10.0, min_track_age_frames=4, required_votes_n=1)
    val = SingleAbilityValidator(cfg, log_file=tmp_path / "test_log.jsonl")

    # 1-frame flicker with track_age=1 (too young, rejected)
    ev = val.process_frame(make_dummy_leap(), track_age=1, timestamp=1.0, frame_idx=1)
    assert ev is None
    assert val.state == ValidatorState.IDLE


def test_validator_drains_window_without_confirmation(tmp_path: Path):
    cfg = AbilityValidatorConfig(ability_id="leap", cooldown_seconds=10.0, required_votes_n=3, window_frames_m=3)
    val = SingleAbilityValidator(cfg, log_file=tmp_path / "test_log.jsonl")

    # Frame 1: 1 vote -> CANDIDATE
    val.process_frame(make_dummy_leap(), track_age=5, timestamp=1.0, frame_idx=1)
    assert val.state == ValidatorState.CANDIDATE

    # Drain window by appending non-detections across window_frames_m (3 frames)
    val.process_frame(None, track_age=5, timestamp=1.033, frame_idx=2)
    val.process_frame(None, track_age=5, timestamp=1.066, frame_idx=3)
    val.process_frame(None, track_age=5, timestamp=1.099, frame_idx=4)
    assert val.state == ValidatorState.IDLE
