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


def test_cooldown_bank_trigger_with_reaction_offset(hidden_killer_config):
    clock = [200.0]
    bank = CooldownBank(time_func=lambda: clock[0])
    bank.set_killer(hidden_killer_config)

    # Trigger with 0.8s reaction offset (user pressed 0.8s after noticing Leap)
    started = bank.trigger("leap", offset=0.8, source="manual")
    assert started is True

    snap = bank.get_snapshot("leap")
    assert snap.state == CooldownState.COOLDOWN
    # Cooldown was 25.0s, remaining should be 25.0 - 0.8 = 24.2s
    assert pytest.approx(snap.remaining_seconds, 0.05) == 24.2

    # Advance clock by 4.2s -> remaining should be 20.0s
    clock[0] = 204.2
    snap2 = bank.get_snapshot("leap")
    assert pytest.approx(snap2.remaining_seconds, 0.05) == 20.0


def test_cooldown_bank_duplicate_suppression_and_restart(hidden_killer_config):
    clock = [300.0]
    bank = CooldownBank(time_func=lambda: clock[0])
    bank.set_killer(hidden_killer_config)

    # 1. Trigger Leap
    assert bank.trigger("leap", offset=0.0) is True

    # Advance clock by 10s -> remaining 15.0s
    clock[0] = 310.0
    assert pytest.approx(bank.get_snapshot("leap").remaining_seconds, 0.05) == 15.0

    # 2. Duplicate trigger with restart_on_repeat=False -> suppressed
    assert bank.trigger("leap", restart_on_repeat=False) is False
    assert pytest.approx(bank.get_snapshot("leap").remaining_seconds, 0.05) == 15.0

    # 3. Trigger with restart_on_repeat=True -> restarted from 25.0s
    assert bank.trigger("leap", restart_on_repeat=True) is True
    assert pytest.approx(bank.get_snapshot("leap").remaining_seconds, 0.05) == 25.0


def test_cooldown_bank_partial_and_full_reset(hidden_killer_config):
    clock = [400.0]
    bank = CooldownBank(time_func=lambda: clock[0])
    bank.set_killer(hidden_killer_config)

    bank.trigger("leap")
    bank.trigger("mark")
    assert bank.get_snapshot("leap").state == CooldownState.COOLDOWN
    assert bank.get_snapshot("mark").state == CooldownState.COOLDOWN

    # Partial reset: only leap
    bank.reset("leap")
    assert bank.get_snapshot("leap").state == CooldownState.READY
    assert bank.get_snapshot("mark").state == CooldownState.COOLDOWN

    # Full reset: all
    bank.reset()
    assert bank.get_snapshot("leap").state == CooldownState.READY
    assert bank.get_snapshot("mark").state == CooldownState.READY


def test_cooldown_bank_snapshots_and_listeners(hidden_killer_config):
    clock = [500.0]
    bank = CooldownBank(time_func=lambda: clock[0])
    bank.set_killer(hidden_killer_config)

    events_received = []
    bank.add_listener(lambda ab_id, snap: events_received.append((ab_id, snap.state)))

    bank.trigger("mark")
    assert len(events_received) >= 1
    assert ("mark", CooldownState.COOLDOWN) in events_received

    # Verify snapshots() returns dict of all
    snaps = bank.snapshots()
    assert "leap" in snaps
    assert "mark" in snaps
    assert snaps["leap"].state == CooldownState.READY
    assert snaps["mark"].state == CooldownState.COOLDOWN

