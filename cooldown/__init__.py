"""Cooldown Package for Violence District Cooldown Tracker.

Provides UI-independent cooldown logic, state machine, event models, and status snapshots.
"""

from cooldown.ability_event import AbilityEvent, InvalidAbilityEventError
from cooldown.cooldown_state import CooldownSnapshot, CooldownState
from cooldown.cooldown_manager import CooldownManager

__all__ = [
    "AbilityEvent",
    "InvalidAbilityEventError",
    "CooldownState",
    "CooldownSnapshot",
    "CooldownManager",
]
