"""Multi-Frame Action Event Validator & Decision State Machine.

Violence District Cooldown Tracker — Rebuild Phase 5 (Task 5.1 & 5.4)
Manages multi-frame voting and refractory suppression:
States: IDLE -> CANDIDATE -> CONFIRMED -> REFRACTORY
Rules:
- Confirmation: N-out-of-M frame agreement (default 3 of 5)
- Track Age Pre-requisite: Track must be alive for >= K frames (suppresses 1-frame spikes)
- Refractory Lockout: Suppresses duplicate triggers during cooldown duration
- Emits normalized AbilityEvent once per confirmed action
- Audit logging to logs/detections.jsonl
"""

from __future__ import annotations

import collections
import enum
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, List, Optional, Union

from cooldown.ability_event import AbilityEvent
from detection.leap_recognizer import LeapCandidate
from detection.mark_recognizer import MarkCandidate

LOG_PATH = Path("logs/detections.jsonl")


class ValidatorState(enum.Enum):
    IDLE = "IDLE"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    REFRACTORY = "REFRACTORY"


@dataclass
class AbilityValidatorConfig:
    ability_id: str
    cooldown_seconds: float
    min_track_age_frames: int = 4
    required_votes_n: int = 3
    window_frames_m: int = 5
    min_score: float = 0.55


class SingleAbilityValidator:
    def __init__(self, config: AbilityValidatorConfig, log_file: Optional[Path] = LOG_PATH) -> None:
        self.config = config
        self.log_file = log_file
        self.state: ValidatorState = ValidatorState.IDLE

        self.candidate_window: Deque[float] = collections.deque(maxlen=config.window_frames_m)
        self.refractory_end_time: float = 0.0

    def reset(self) -> None:
        self.state = ValidatorState.IDLE
        self.candidate_window.clear()
        self.refractory_end_time = 0.0

    def cancel(self) -> None:
        self.reset()

    def process_frame(
        self,
        candidate: Optional[Union[LeapCandidate, MarkCandidate]],
        track_age: int,
        timestamp: float,
        frame_idx: int,
    ) -> Optional[AbilityEvent]:
        # Check refractory expiration
        if self.state == ValidatorState.REFRACTORY:
            if timestamp >= self.refractory_end_time:
                self.state = ValidatorState.IDLE
                self._log_decision(timestamp, frame_idx, "REFRACTORY_EXPIRED", "Cooldown completed, returned to IDLE")
            else:
                # Still in cooldown lockout: ignore any candidate
                return None

        # Track age check (suppresses single-frame noise artifacts)
        if candidate is not None and track_age < self.config.min_track_age_frames:
            self._log_decision(timestamp, frame_idx, "REJECT_PREMATURE_TRACK", f"Track age {track_age} < min {self.config.min_track_age_frames}")
            candidate = None

        # Voting buffer update
        if candidate is not None and candidate.score >= self.config.min_score:
            self.candidate_window.append(candidate.score)
        else:
            self.candidate_window.append(0.0)

        positive_votes = sum(1 for s in self.candidate_window if s >= self.config.min_score)

        if self.state == ValidatorState.IDLE:
            if positive_votes >= 1:
                self.state = ValidatorState.CANDIDATE
                self._log_decision(timestamp, frame_idx, "STATE_CANDIDATE", f"First candidate vote (score {candidate.score if candidate else 0:.2f})")

        if self.state == ValidatorState.CANDIDATE:
            if positive_votes >= self.config.required_votes_n:
                # CONFIRMED! Emit AbilityEvent and transition to REFRACTORY
                avg_score = float(sum(s for s in self.candidate_window if s > 0) / max(1, positive_votes))
                self.state = ValidatorState.REFRACTORY
                self.refractory_end_time = timestamp + self.config.cooldown_seconds
                self.candidate_window.clear()

                self._log_decision(
                    timestamp,
                    frame_idx,
                    "ACTION_CONFIRMED",
                    f"{self.config.ability_id} confirmed ({positive_votes}/{self.config.window_frames_m} votes, avg score {avg_score:.2f}). Refractory until {self.refractory_end_time:.2f}",
                )

                return AbilityEvent(
                    killer_id="the_hidden",
                    ability_id=self.config.ability_id,
                    event_type="cast_start",
                    timestamp=round(timestamp, 3),
                    confidence=round(avg_score, 3),
                    source="vision",
                )
            elif positive_votes == 0:
                # No positive votes currently in window: revert to IDLE
                self.state = ValidatorState.IDLE
                self._log_decision(timestamp, frame_idx, "CANDIDATE_DRAINED", "No votes remaining in window, returned to IDLE")

        return None

    def _log_decision(self, timestamp: float, frame_idx: int, event_type: str, reason: str) -> None:
        if self.log_file is None:
            return
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "timestamp": round(timestamp, 3),
                "frame_idx": frame_idx,
                "ability_id": self.config.ability_id,
                "state": self.state.value,
                "event_type": event_type,
                "reason": reason,
            }
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass


class EventValidator:
    """Multi-ability action validator coordinating individual ability state machines."""

    def __init__(self, log_file: Optional[Path] = LOG_PATH) -> None:
        self.log_file = log_file
        self.validators: Dict[str, SingleAbilityValidator] = {
            "leap": SingleAbilityValidator(
                AbilityValidatorConfig(
                    ability_id="leap",
                    cooldown_seconds=25.0,  # The Hidden Leap standard cooldown
                    min_track_age_frames=4,
                    required_votes_n=3,
                    window_frames_m=5,
                    min_score=0.55,
                ),
                log_file=self.log_file,
            ),
            "mark": SingleAbilityValidator(
                AbilityValidatorConfig(
                    ability_id="mark",
                    cooldown_seconds=15.0,  # The Hidden Mark standard cooldown
                    min_track_age_frames=4,
                    required_votes_n=3,
                    window_frames_m=5,
                    min_score=0.55,
                ),
                log_file=self.log_file,
            ),
        }

    def process(
        self,
        leap_candidate: Optional[LeapCandidate],
        mark_candidate: Optional[MarkCandidate],
        track_age: int,
        timestamp: float,
        frame_idx: int,
    ) -> List[AbilityEvent]:
        emitted: List[AbilityEvent] = []

        # Process Leap
        leap_val = self.validators.get("leap")
        if leap_val:
            ev = leap_val.process_frame(leap_candidate, track_age, timestamp, frame_idx)
            if ev:
                emitted.append(ev)

        # Process Mark
        mark_val = self.validators.get("mark")
        if mark_val:
            ev = mark_val.process_frame(mark_candidate, track_age, timestamp, frame_idx)
            if ev:
                emitted.append(ev)

        return emitted

    def reset(self) -> None:
        for val in self.validators.values():
            val.reset()

    def cancel(self, ability_id: Optional[str] = None) -> None:
        if ability_id:
            val = self.validators.get(ability_id)
            if val:
                val.cancel()
        else:
            self.reset()
