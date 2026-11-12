"""Unit Tests for CooldownState and CooldownSnapshot.

Week 2 — Day 8 (Desain Kontrak Cooldown)
Verifies enum definitions, snapshot properties, formatting, and numeric clamping.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cooldown.cooldown_state import CooldownSnapshot, CooldownState


class TestCooldownState(unittest.TestCase):
    """Test suite untuk model status CooldownState dan CooldownSnapshot."""

    def test_cooldown_state_enum_values(self) -> None:
        """Memastikan seluruh state diskrit didefinisikan dengan benar."""
        self.assertEqual(CooldownState.READY.value, "READY")
        self.assertEqual(CooldownState.WAITING_FOR_RELEASE.value, "WAITING_FOR_RELEASE")
        self.assertEqual(CooldownState.COOLDOWN.value, "COOLDOWN")
        self.assertEqual(CooldownState.DISABLED.value, "DISABLED")

    def test_snapshot_ready_state(self) -> None:
        """Memastikan properti snapshot saat status READY."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.READY,
            remaining_seconds=0.0,
            total_cooldown_seconds=25.0,
            progress=0.0,
            trigger_type="on_cast_start",
            verified=False,
        )
        self.assertTrue(snap.is_ready)
        self.assertFalse(snap.is_active)
        self.assertFalse(snap.is_waiting_for_release)
        self.assertEqual(snap.formatted_remaining, "READY")

    def test_snapshot_active_cooldown_state(self) -> None:
        """Memastikan properti snapshot saat cooldown aktif."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.COOLDOWN,
            remaining_seconds=12.5,
            total_cooldown_seconds=25.0,
            progress=0.5,
            trigger_type="on_cast_start",
        )
        self.assertFalse(snap.is_ready)
        self.assertTrue(snap.is_active)
        self.assertFalse(snap.is_waiting_for_release)
        self.assertEqual(snap.formatted_remaining, "12.5s")

    def test_snapshot_waiting_for_release_state(self) -> None:
        """Memastikan properti snapshot saat menunggu release (stance aktif)."""
        snap = CooldownSnapshot(
            killer_id="veil",
            ability_id="through_the_veil",
            ability_name="Through The Veil",
            state=CooldownState.WAITING_FOR_RELEASE,
            remaining_seconds=20.0,
            total_cooldown_seconds=20.0,
            progress=1.0,
            trigger_type="on_release",
        )
        self.assertFalse(snap.is_ready)
        self.assertTrue(snap.is_active)
        self.assertTrue(snap.is_waiting_for_release)
        self.assertEqual(snap.formatted_remaining, "AIMING")

    def test_snapshot_clamping_prevents_negative_or_overflow_values(self) -> None:
        """Memastikan sisa detik negatif dan progress di luar rentang di-clamp aman."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.COOLDOWN,
            remaining_seconds=-2.5,
            total_cooldown_seconds=-10.0,
            progress=1.5,
            trigger_type="on_cast_start",
        )
        self.assertEqual(snap.remaining_seconds, 0.0)
        self.assertEqual(snap.total_cooldown_seconds, 0.0)
        self.assertEqual(snap.progress, 1.0)

    def test_snapshot_is_immutable(self) -> None:
        """Memastikan snapshot bersifat frozen dan tidak dapat dimutasi UI."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.READY,
            remaining_seconds=0.0,
            total_cooldown_seconds=25.0,
            progress=0.0,
            trigger_type="on_cast_start",
        )
        with self.assertRaises(AttributeError):
            snap.remaining_seconds = 10.0  # type: ignore


if __name__ == "__main__":
    unittest.main()
