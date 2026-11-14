"""Unit tests for Multi-Ability CooldownBank (cooldown/cooldown_bank.py)."""

import pytest

from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_bank import CooldownBank
from cooldown.cooldown_state import CooldownState
from database.database_manager import AbilityConfig, KillerConfig


@pytest.fixture
def hidden_killer_config() -> KillerConfig:
    return KillerConfig(
        id="the_hidden",
        name="The Hidden",
        abilities=[
            AbilityConfig(
                id="leap",
                name="Leap",
                cooldown_seconds=25.0,
                trigger_type="on_cast_start",
            ),
            AbilityConfig(
                id="mark",
                name="Mark",
                cooldown_seconds=15.0,
                trigger_type="on_cast_start",
            ),
        ],
    )


def test_cooldown_bank_multi_ability_registration(hidden_killer_config):
    bank = CooldownBank()
    bank.set_killer(hidden_killer_config)

    assert "leap" in bank.managers
    assert "mark" in bank.managers
    assert bank.get_snapshot("leap").state == CooldownState.READY
    assert bank.get_snapshot("mark").state == CooldownState.READY


def test_cooldown_bank_independent_ability_tracking(hidden_killer_config):
    clock = [100.0]
    bank = CooldownBank(time_func=lambda: clock[0])
    bank.set_killer(hidden_killer_config)

    # 1. Trigger Leap
    ev_leap = AbilityEvent(
        killer_id="the_hidden",
        ability_id="leap",
        event_type="cast_start",
        source="vision",
        confidence=0.9,
        timestamp=clock[0],
    )
    handled_leap = bank.handle_event(ev_leap)
    assert handled_leap is True

    # Leap must be on COOLDOWN, Mark must remain READY!
    snap_leap = bank.get_snapshot("leap")
    snap_mark = bank.get_snapshot("mark")
    assert snap_leap.state == CooldownState.COOLDOWN
    assert snap_leap.remaining_seconds == 25.0
    assert snap_mark.state == CooldownState.READY

    # 2. Advance clock by 5s and trigger Mark
    clock[0] = 105.0
    ev_mark = AbilityEvent(
        killer_id="the_hidden",
        ability_id="mark",
        event_type="cast_start",
        source="vision",
        confidence=0.85,
        timestamp=clock[0],
    )
    handled_mark = bank.handle_event(ev_mark)
    assert handled_mark is True

    # Both are on cooldown with independent remaining seconds!
    snap_leap2 = bank.get_snapshot("leap")
    snap_mark2 = bank.get_snapshot("mark")
    assert snap_leap2.state == CooldownState.COOLDOWN
    assert pytest.approx(snap_leap2.remaining_seconds, 0.1) == 20.0  # 25 - 5
    assert snap_mark2.state == CooldownState.COOLDOWN
    assert pytest.approx(snap_mark2.remaining_seconds, 0.1) == 15.0
