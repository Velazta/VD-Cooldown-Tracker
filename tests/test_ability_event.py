"""Unit Tests for Normalized AbilityEvent Contract.

Week 2 — Day 8 (Desain Kontrak Cooldown)
Verifies creation, validation, immutability, and boundary rules for ability events.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cooldown.ability_event import AbilityEvent, InvalidAbilityEventError


class TestAbilityEvent(unittest.TestCase):
    """Test suite untuk validasi model data AbilityEvent."""

    def test_valid_ability_event_creation(self) -> None:
        """Memastikan pembuatan AbilityEvent valid berhasil dengan nilai yang tepat."""
        event = AbilityEvent(
            killer_id="the_hidden",
            ability_id="leap",
            event_type="cast_start",
            timestamp=100.5,
            confidence=0.95,
            source="manual",
        )
        self.assertEqual(event.killer_id, "the_hidden")
        self.assertEqual(event.ability_id, "leap")
        self.assertEqual(event.event_type, "cast_start")
        self.assertEqual(event.timestamp, 100.5)
        self.assertEqual(event.confidence, 0.95)
        self.assertEqual(event.source, "manual")

    def test_factory_method_uses_monotonic_time(self) -> None:
        """Memastikan factory create() mengisi timestamp monotonic saat None."""
        t_before = time.monotonic()
        event = AbilityEvent.create(
            killer_id="veil",
            ability_id="through_the_veil",
            event_type="release",
        )
        t_after = time.monotonic()

        self.assertGreaterEqual(event.timestamp, t_before)
        self.assertLessEqual(event.timestamp, t_after)
        self.assertEqual(event.confidence, 1.0)
        self.assertEqual(event.source, "manual")

    def test_empty_killer_id_raises_error(self) -> None:
        """Memastikan killer_id kosong melempar InvalidAbilityEventError."""
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="",
                ability_id="leap",
                event_type="cast_start",
                timestamp=100.0,
            )

    def test_empty_ability_id_raises_error(self) -> None:
        """Memastikan ability_id kosong melempar InvalidAbilityEventError."""
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="the_hidden",
                ability_id="",
                event_type="cast_start",
                timestamp=100.0,
            )

    def test_invalid_event_type_raises_error(self) -> None:
        """Memastikan event_type tidak dikenal melempar InvalidAbilityEventError."""
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="the_hidden",
                ability_id="leap",
                event_type="jump_attack",
                timestamp=100.0,
            )

    def test_invalid_timestamp_raises_error(self) -> None:
        """Memastikan timestamp <= 0 melempar InvalidAbilityEventError."""
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="the_hidden",
                ability_id="leap",
                event_type="cast_start",
                timestamp=-5.0,
            )

    def test_confidence_out_of_bounds_raises_error(self) -> None:
        """Memastikan confidence di luar rentang [0.0, 1.0] melempar error."""
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="the_hidden",
                ability_id="leap",
                event_type="cast_start",
                timestamp=10.0,
                confidence=1.5,
            )
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="the_hidden",
                ability_id="leap",
                event_type="cast_start",
                timestamp=10.0,
                confidence=-0.1,
            )

    def test_invalid_source_raises_error(self) -> None:
        """Memastikan source tidak terdaftar melempar error."""
        with self.assertRaises(InvalidAbilityEventError):
            AbilityEvent(
                killer_id="the_hidden",
                ability_id="leap",
                event_type="cast_start",
                timestamp=10.0,
                source="unknown_injector",
            )

    def test_event_is_immutable(self) -> None:
        """Memastikan instance AbilityEvent bersifat immutable (frozen=True)."""
        event = AbilityEvent.create("the_hidden", "leap", "cast_start")
        with self.assertRaises(AttributeError):
            event.killer_id = "veil"  # type: ignore


if __name__ == "__main__":
    unittest.main()
