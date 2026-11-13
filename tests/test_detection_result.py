"""Unit Tests for DetectionResult and AbilityEvent Adapter Contract.

Violence District Cooldown Tracker — Week 3 (Day 17)
Verifies:
- DetectionResult validation and integrity
- Clean adapter mapping into AbilityEvent with source='vision'
- Decoupling from Qt and UI layers
"""

from __future__ import annotations

import time
import unittest

from cooldown.ability_event import AbilityEvent
from detection.detection_result import DetectionResult


class TestDetectionResult(unittest.TestCase):
    """Test suite untuk DetectionResult dan konversi AbilityEvent."""

    def test_detection_result_valid_instantiation(self) -> None:
        """Memastikan instantiasi valid dengan seluruh metadata bukti."""
        now = time.monotonic()
        res = DetectionResult(
            killer_id="the_hidden",
            ability_id="leap",
            event_type="cast_start",
            timestamp=now,
            confidence=0.88,
            source="vision",
            evidence={"template_id": "template_leap_airborne_var1", "score": 0.88},
        )
        self.assertEqual(res.killer_id, "the_hidden")
        self.assertEqual(res.ability_id, "leap")
        self.assertEqual(res.event_type, "cast_start")
        self.assertEqual(res.timestamp, now)
        self.assertEqual(res.confidence, 0.88)
        self.assertEqual(res.source, "vision")
        self.assertEqual(res.evidence["score"], 0.88)

    def test_to_ability_event_adapter_mapping(self) -> None:
        """Memastikan konversi ke AbilityEvent memenuhi kontrak cooldown manager."""
        now = time.monotonic()
        res = DetectionResult(
            killer_id="the_hidden",
            ability_id="leap",
            event_type="cast_start",
            timestamp=now,
            confidence=0.92,
            source="vision",
        )

        event = res.to_ability_event()
        self.assertIsInstance(event, AbilityEvent)
        self.assertEqual(event.killer_id, "the_hidden")
        self.assertEqual(event.ability_id, "leap")
        self.assertEqual(event.event_type, "cast_start")
        self.assertEqual(event.timestamp, now)
        self.assertEqual(event.confidence, 0.92)
        self.assertEqual(event.source, "vision")

    def test_invalid_parameters_raise_error(self) -> None:
        """Memastikan validasi menolak parameter yang tidak valid."""
        now = time.monotonic()
        # Invalid confidence
        with self.assertRaises(ValueError):
            DetectionResult("the_hidden", "leap", "cast_start", now, confidence=1.5)

        # Invalid event type
        with self.assertRaises(ValueError):
            DetectionResult("the_hidden", "leap", "invalid_action", now, confidence=0.8)

        # Negative timestamp
        with self.assertRaises(ValueError):
            DetectionResult("the_hidden", "leap", "cast_start", -10.0, confidence=0.8)


if __name__ == "__main__":
    unittest.main()
