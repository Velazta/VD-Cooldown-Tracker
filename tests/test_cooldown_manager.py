"""Unit Tests for Cooldown State Machine.

Week 2 — Day 9 (Cooldown State Machine)
Verifies:
- Monotonic elapsed-time calculations without drift
- 'on_cast_start' trigger semantics (The Hidden -> Leap)
- 'on_release' trigger semantics (Veil -> Through The Veil)
- Duplicate event suppression during active cooldown
- Reset and cancel deterministic behavior
- Mock clock time progression
- Listener notifications
- Complete independence from PySide6 / OpenCV
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cooldown import (
    AbilityEvent,
    CooldownManager,
    CooldownSnapshot,
    CooldownState,
)
from database.database_manager import AbilityConfig


class TestCooldownManager(unittest.TestCase):
    """Test suite untuk CooldownManager dengan controlled mock clock."""

    def setUp(self) -> None:
        self.current_time = 1000.0

        def mock_clock() -> float:
            return self.current_time

        self.mock_clock = mock_clock
        self.manager = CooldownManager(time_func=self.mock_clock)

        # Kemampuan tipe on_cast_start (The Hidden -> Leap)
        self.leap_ability = AbilityConfig(
            id="leap",
            name="Leap",
            cooldown_seconds=25.0,
            cooldown_verified=False,
            enabled=True,
            trigger_type="on_cast_start",
            interact_input="E Button",
        )

        # Kemampuan tipe on_release (Veil -> Through The Veil)
        self.veil_ability = AbilityConfig(
            id="through_the_veil",
            name="Through The Veil",
            cooldown_seconds=20.0,
            cooldown_verified=False,
            enabled=True,
            trigger_type="on_release",
            interact_input="Aim & Throw Spear",
        )

    def test_initial_state_is_ready(self) -> None:
        """Memastikan status awal kemampuan aktif adalah READY."""
        self.manager.set_ability(killer_id="the_hidden", ability=self.leap_ability)
        self.assertEqual(self.manager.state, CooldownState.READY)
        snap = self.manager.get_snapshot()
        self.assertTrue(snap.is_ready)
        self.assertFalse(snap.is_active)
        self.assertEqual(snap.remaining_seconds, 0.0)
        self.assertEqual(snap.progress, 0.0)
        self.assertEqual(snap.formatted_remaining, "READY")

    def test_on_cast_start_full_cycle(self) -> None:
        """Memastikan alur on_cast_start: READY -> COOLDOWN -> EXPIRED -> READY."""
        self.manager.set_ability("the_hidden", self.leap_ability)

        # 1. Pemicuan event cast_start pada t=1000.0
        event = AbilityEvent.create(
            killer_id="the_hidden",
            ability_id="leap",
            event_type="cast_start",
            timestamp=self.current_time,
        )
        handled = self.manager.handle_event(event)
        self.assertTrue(handled)
        self.assertEqual(self.manager.state, CooldownState.COOLDOWN)

        # 2. Majukan waktu 10 detik (t=1010.0) -> sisa 15 detik
        self.current_time += 10.0
        snap = self.manager.get_snapshot()
        self.assertEqual(self.manager.state, CooldownState.COOLDOWN)
        self.assertAlmostEqual(snap.remaining_seconds, 15.0, places=2)
        self.assertAlmostEqual(snap.progress, 15.0 / 25.0, places=2)
        self.assertEqual(snap.formatted_remaining, "15.0s")

        # 3. Majukan waktu hingga tepat sebelum expiry (t=1024.9)
        self.current_time = 1024.9
        self.assertEqual(self.manager.state, CooldownState.COOLDOWN)
        self.assertAlmostEqual(self.manager.get_snapshot().remaining_seconds, 0.1, places=1)

        # 4. Majukan waktu melewati durasi cooldown (t=1025.1) -> Otomatis READY
        self.current_time = 1025.1
        self.assertEqual(self.manager.state, CooldownState.READY)
        final_snap = self.manager.get_snapshot()
        self.assertTrue(final_snap.is_ready)
        self.assertEqual(final_snap.remaining_seconds, 0.0)
        self.assertEqual(final_snap.formatted_remaining, "READY")

    def test_on_release_full_cycle(self) -> None:
        """Memastikan alur on_release: READY -> WAITING_FOR_RELEASE -> COOLDOWN -> READY."""
        self.manager.set_ability("veil", self.veil_ability)

        # 1. Event cast_start (mengangkat tombak / stance) pada t=1000.0
        start_event = AbilityEvent.create(
            killer_id="veil",
            ability_id="through_the_veil",
            event_type="cast_start",
            timestamp=self.current_time,
        )
        handled = self.manager.handle_event(start_event)
        self.assertTrue(handled)
        self.assertEqual(self.manager.state, CooldownState.WAITING_FOR_RELEASE)

        # Sisa waktu harus tetap 20.0s selama fase aiming
        self.current_time += 4.0
        snap_aiming = self.manager.get_snapshot()
        self.assertEqual(snap_aiming.state, CooldownState.WAITING_FOR_RELEASE)
        self.assertEqual(snap_aiming.remaining_seconds, 20.0)
        self.assertEqual(snap_aiming.formatted_remaining, "AIMING")

        # 2. Event release (melempar tombak) pada t=1004.0
        release_event = AbilityEvent.create(
            killer_id="veil",
            ability_id="through_the_veil",
            event_type="release",
            timestamp=self.current_time,
        )
        handled_release = self.manager.handle_event(release_event)
        self.assertTrue(handled_release)
        self.assertEqual(self.manager.state, CooldownState.COOLDOWN)

        # 3. Majukan waktu 10 detik (t=1014.0) -> sisa 10 detik
        self.current_time += 10.0
        snap_cooldown = self.manager.get_snapshot()
        self.assertAlmostEqual(snap_cooldown.remaining_seconds, 10.0, places=2)
        self.assertEqual(snap_cooldown.formatted_remaining, "10.0s")

        # 4. Majukan waktu hingga cooldown selesai (t=1024.0)
        self.current_time += 10.0
        self.assertEqual(self.manager.state, CooldownState.READY)
        self.assertTrue(self.manager.get_snapshot().is_ready)

    def test_duplicate_event_suppression(self) -> None:
        """Memastikan spam event saat cooldown aktif ditekan dan tidak me-restart deadline."""
        self.manager.set_ability("the_hidden", self.leap_ability)

        # Start cooldown pada t=1000.0 (deadline = 1025.0)
        event1 = AbilityEvent.create("the_hidden", "leap", "cast_start", timestamp=1000.0)
        self.manager.handle_event(event1)

        # Di tengah jalan pada t=1010.0 (sisa 15 detik), tiba event cast_start duplikat
        self.current_time = 1010.0
        event_dup = AbilityEvent.create("the_hidden", "leap", "cast_start", timestamp=1010.0)
        handled = self.manager.handle_event(event_dup)

        # Event harus ditekan (return False)
        self.assertFalse(handled)

        # Sisa detik harus tetap dihitung dari deadline awal (1025.0 - 1010.0 = 15.0 detik)
        # TIDAK BOLEH ter-reset menjadi 25.0 detik!
        snap = self.manager.get_snapshot()
        self.assertAlmostEqual(snap.remaining_seconds, 15.0, places=2)

    def test_cancel_event_resets_to_ready(self) -> None:
        """Memastikan event cancel atau pemanggilan cancel() mengembalikan state ke READY."""
        self.manager.set_ability("the_hidden", self.leap_ability)
        event = AbilityEvent.create("the_hidden", "leap", "cast_start", timestamp=1000.0)
        self.manager.handle_event(event)
        self.assertEqual(self.manager.state, CooldownState.COOLDOWN)

        # Kirim event cancel
        cancel_event = AbilityEvent.create("the_hidden", "leap", "cancel", timestamp=1005.0)
        handled = self.manager.handle_event(cancel_event)
        self.assertTrue(handled)
        self.assertEqual(self.manager.state, CooldownState.READY)
        self.assertEqual(self.manager.get_snapshot().remaining_seconds, 0.0)

    def test_mismatched_event_is_ignored(self) -> None:
        """Memastikan event untuk killer atau ability lain diabaikan secara aman."""
        self.manager.set_ability("the_hidden", self.leap_ability)

        mismatched_event = AbilityEvent.create(
            killer_id="other_killer",
            ability_id="leap",
            event_type="cast_start",
            timestamp=1000.0,
        )
        self.assertFalse(self.manager.handle_event(mismatched_event))
        self.assertEqual(self.manager.state, CooldownState.READY)

    def test_disabled_ability_state(self) -> None:
        """Memastikan ability berstatus disabled tidak dapat dipicu."""
        disabled_ability = AbilityConfig(
            id="mark",
            name="Mark",
            cooldown_seconds=30.0,
            enabled=False,
            trigger_type="on_cast_start",
        )
        self.manager.set_ability("the_hidden", disabled_ability)
        self.assertEqual(self.manager.state, CooldownState.DISABLED)

        event = AbilityEvent.create("the_hidden", "mark", "cast_start", timestamp=1000.0)
        self.assertFalse(self.manager.handle_event(event))
        self.assertEqual(self.manager.state, CooldownState.DISABLED)
        self.assertEqual(self.manager.get_snapshot().formatted_remaining, "DISABLED")

    def test_listener_notification_callback(self) -> None:
        """Memastikan listener callback dipanggil setiap kali terjadi transisi status."""
        notifications: list[CooldownSnapshot] = []

        def listener(snap: CooldownSnapshot) -> None:
            notifications.append(snap)

        self.manager.add_listener(listener)
        self.manager.set_ability("the_hidden", self.leap_ability)
        self.assertGreaterEqual(len(notifications), 1)

        # Pemicuan cooldown harus memanggil listener
        event = AbilityEvent.create("the_hidden", "leap", "cast_start", timestamp=1000.0)
        self.manager.handle_event(event)
        self.assertGreaterEqual(len(notifications), 2)
        self.assertEqual(notifications[-1].state, CooldownState.COOLDOWN)

        # Expiry cooldown harus memanggil listener
        self.current_time = 1026.0
        self.assertEqual(self.manager.state, CooldownState.READY)
        self.assertEqual(notifications[-1].state, CooldownState.READY)


if __name__ == "__main__":
    unittest.main()
