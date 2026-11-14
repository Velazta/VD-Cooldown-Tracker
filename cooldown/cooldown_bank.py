"""Multi-Ability Cooldown Bank Manager.

Violence District Cooldown Tracker — Rebuild Phase 5 (Task 5.2)
Manages independent CooldownManager instances for all abilities of an active killer
(e.g., Leap and Mark for The Hidden), allowing concurrent tracking without cross-ability blocking.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_manager import CooldownManager
from cooldown.cooldown_state import CooldownSnapshot
from database.database_manager import AbilityConfig, KillerConfig


class CooldownBank:
    """Multi-ability cooldown bank managing discrete state machines per ability."""

    def __init__(self, time_func: Optional[Callable[[], float]] = None) -> None:
        self._time_func = time_func or time.monotonic
        self.killer_id: str = ""
        self.managers: Dict[str, CooldownManager] = {}
        self._listeners: List[Callable[[str, CooldownSnapshot], None]] = []

    def set_killer(self, killer: KillerConfig) -> None:
        """Configures the bank for a specific killer, creating managers for each ability."""
        self.killer_id = killer.id
        self.managers.clear()

        for ab in killer.abilities:
            mgr = CooldownManager(time_func=self._time_func)
            mgr.set_ability(self.killer_id, ab)
            # Forward individual manager notifications to bank listeners
            ab_id = ab.id
            mgr.add_listener(lambda snap, a_id=ab_id: self._notify_listeners(a_id, snap))
            self.managers[ab_id] = mgr

    def add_manager(self, ability_id: str, manager: CooldownManager) -> None:
        """Manually registers an existing manager."""
        self.managers[ability_id] = manager
        manager.add_listener(lambda snap, a_id=ability_id: self._notify_listeners(a_id, snap))

    def get_manager(self, ability_id: str) -> Optional[CooldownManager]:
        return self.managers.get(ability_id)

    def handle_event(self, event: AbilityEvent) -> bool:
        """Routes an ability event to its matching ability manager."""
        mgr = self.managers.get(event.ability_id)
        if mgr is not None:
            return mgr.handle_event(event)
        return False

    def get_snapshot(self, ability_id: str) -> Optional[CooldownSnapshot]:
        mgr = self.managers.get(ability_id)
        return mgr.get_snapshot() if mgr is not None else None

    def get_all_snapshots(self) -> Dict[str, CooldownSnapshot]:
        return {ab_id: mgr.get_snapshot() for ab_id, mgr in self.managers.items()}

    def reset_all(self) -> None:
        for mgr in self.managers.values():
            mgr.reset()

    def subscribe(self, callback: Callable[[str, CooldownSnapshot], None]) -> None:
        """Subscribes to updates across all managed abilities."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _notify_listeners(self, ability_id: str, snapshot: CooldownSnapshot) -> None:
        for listener in self._listeners:
            try:
                listener(ability_id, snapshot)
            except Exception:
                pass
