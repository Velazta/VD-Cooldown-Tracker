"""Unit Tests for CooldownWidget.

Week 2 — Day 11 (Cooldown Widget)
Runs headless via PySide6 offscreen platform to verify:
- Widget initialization and snapshot updates
- Rendering of READY, COOLDOWN, WAITING_FOR_RELEASE, and DISABLED states
- Repainting execution without exceptions
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force offscreen rendering for headless CI / unit test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from cooldown.cooldown_state import CooldownSnapshot, CooldownState
from overlay.cooldown_widget import CooldownWidget


class TestCooldownWidget(unittest.TestCase):
    """Test suite untuk widget CooldownWidget."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.widget = CooldownWidget()
        self.widget.resize(180, 180)

    def tearDown(self) -> None:
        self.widget.close()

    def test_widget_initial_state(self) -> None:
        """Memastikan widget baru belum memiliki snapshot dan ukuran minimum valid."""
        self.assertIsNone(self.widget.snapshot)
        self.assertGreaterEqual(self.widget.minimumWidth(), 120)
        self.assertGreaterEqual(self.widget.minimumHeight(), 120)

    def test_update_snapshot_and_render_ready(self) -> None:
        """Memastikan update snapshot status READY terpasang dan dapat dirender."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.READY,
            remaining_seconds=0.0,
            total_cooldown_seconds=25.0,
            progress=0.0,
            trigger_type="on_cast_start",
            verified=True,
        )
        self.widget.update_snapshot(snap)
        self.assertEqual(self.widget.snapshot, snap)

        # Trigger paint event (render ke buffer offscreen)
        self.widget.repaint()

    def test_render_cooldown_active_state(self) -> None:
        """Memastikan status COOLDOWN dengan sisa waktu aktif dapat dirender."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.COOLDOWN,
            remaining_seconds=18.5,
            total_cooldown_seconds=25.0,
            progress=18.5 / 25.0,
            trigger_type="on_cast_start",
            verified=False,
        )
        self.widget.update_snapshot(snap)
        self.assertEqual(self.widget.snapshot.state, CooldownState.COOLDOWN)
        self.widget.repaint()

    def test_render_waiting_for_release_state(self) -> None:
        """Memastikan status WAITING_FOR_RELEASE dapat dirender."""
        snap = CooldownSnapshot(
            killer_id="veil",
            ability_id="through_the_veil",
            ability_name="Through The Veil",
            state=CooldownState.WAITING_FOR_RELEASE,
            remaining_seconds=20.0,
            total_cooldown_seconds=20.0,
            progress=1.0,
            trigger_type="on_release",
            verified=False,
        )
        self.widget.update_snapshot(snap)
        self.assertEqual(self.widget.snapshot.state, CooldownState.WAITING_FOR_RELEASE)
        self.widget.repaint()

    def test_render_disabled_state(self) -> None:
        """Memastikan status DISABLED dapat dirender."""
        snap = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="mark",
            ability_name="Mark",
            state=CooldownState.DISABLED,
            remaining_seconds=0.0,
            total_cooldown_seconds=30.0,
            progress=0.0,
            trigger_type="on_cast_start",
        )
        self.widget.update_snapshot(snap)
        self.assertEqual(self.widget.snapshot.state, CooldownState.DISABLED)
        self.widget.repaint()


if __name__ == "__main__":
    unittest.main()
