"""Multi-Ability Cooldown Bank Manager.

Violence District Cooldown Tracker — Manual Trigger Milestone (Phase M1)
Manages independent CooldownManager instances for all abilities of an active killer
(e.g., Leap and Mark for The Hidden), allowing concurrent tracking without cross-ability blocking.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from app.logger import get_logger
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_manager import CooldownManager
from cooldown.cooldown_state import CooldownSnapshot
from database.database_manager import AbilityConfig, KillerConfig

logger = get_logger("cooldown_bank")


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

        logger.info("Configured CooldownBank for '%s' with %d abilities.", killer.id, len(killer.abilities))

    def load_killer(self, killer_id: str, db_manager: Optional[Any] = None) -> bool:
        """Loads killer configuration by ID with user overrides applied."""
        from database.database_manager import DatabaseManager
        from database.overrides import apply_overrides_to_killer, load_user_overrides

        db = db_manager if db_manager is not None else DatabaseManager()
        killer = db.get_killer(killer_id)
        if killer is None:
            logger.warning("Killer '%s' not found in database.", killer_id)
            return False

        overridden_killer = apply_overrides_to_killer(killer, load_user_overrides())
        self.set_killer(overridden_killer)
        return True

    def add_manager(self, ability_id: str, manager: CooldownManager) -> None:
        """Manually registers an existing manager."""
        self.managers[ability_id] = manager
        manager.add_listener(lambda snap, a_id=ability_id: self._notify_listeners(a_id, snap))

    def get_manager(self, ability_id: str) -> Optional[CooldownManager]:
        """Returns the CooldownManager for a specific ability ID."""
        return self.managers.get(ability_id)

    def trigger(
        self,
        ability_id: str,
        offset: float = 0.0,
        source: str = "manual",
        restart_on_repeat: bool = False,
    ) -> bool:
        """Triggers cooldown for a specific ability in the bank.
        
        Args:
            ability_id: The ID of the ability to trigger (e.g. 'leap', 'mark').
            offset: Reaction offset in seconds (e.g. 0.5s late press).
            source: Source of the trigger ('manual', 'hotkey', etc.).
            restart_on_repeat: Whether to restart an already active cooldown.
            
        Returns:
            bool: True if cooldown started/restarted, False if ignored or ability not found.
        """
        mgr = self.managers.get(ability_id)
        if mgr is None:
            logger.warning("Trigger failed: Ability '%s' not found in bank.", ability_id)
            return False

        return mgr.trigger(elapsed_offset=offset, source=source, restart_on_repeat=restart_on_repeat)

    def handle_event(self, event: AbilityEvent) -> bool:
        """Routes an ability event to its matching ability manager."""
        mgr = self.managers.get(event.ability_id)
        if mgr is not None:
            return mgr.handle_event(event)
        return False

    def reset(self, ability_id: Optional[str] = None) -> None:
        """Resets cooldowns. If ability_id is specified, resets only that ability; otherwise resets all."""
        if ability_id is not None:
            mgr = self.managers.get(ability_id)
            if mgr is not None:
                mgr.reset()
        else:
            self.reset_all()

    def reset_all(self) -> None:
        """Resets all managers in the bank back to READY."""
        for mgr in self.managers.values():
            mgr.reset()

    def get_snapshot(self, ability_id: str) -> Optional[CooldownSnapshot]:
        """Gets current snapshot for a single ability."""
        mgr = self.managers.get(ability_id)
        return mgr.get_snapshot() if mgr is not None else None

    def get_all_snapshots(self) -> Dict[str, CooldownSnapshot]:
        """Gets current snapshots for all abilities in the bank."""
        return {ab_id: mgr.get_snapshot() for ab_id, mgr in self.managers.items()}

    def snapshots(self) -> Dict[str, CooldownSnapshot]:
        """Convenience alias for get_all_snapshots()."""
        return self.get_all_snapshots()

    def add_listener(self, callback: Callable[[str, CooldownSnapshot], None]) -> None:
        """Subscribes to updates across all managed abilities: callback(ability_id, snapshot)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str, CooldownSnapshot], None]) -> None:
        """Unsubscribes a listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def subscribe(self, callback: Callable[[str, CooldownSnapshot], None]) -> None:
        """Alias for add_listener."""
        self.add_listener(callback)

    def _notify_listeners(self, ability_id: str, snapshot: CooldownSnapshot) -> None:
        for listener in self._listeners:
            try:
                listener(ability_id, snapshot)
            except Exception as exc:
                logger.error("Error in bank listener callback: %s", exc)
