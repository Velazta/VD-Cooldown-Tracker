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

    def test_popup_banner_path_mapping(self) -> None:
        """Memastikan template banner untuk setiap killer dan skill terpetakan dengan benar."""
        from overlay.popup_banner import resolve_banner_path, BANNER_FILE_MAP

        self.assertIn(("the_hidden", "leap"), BANNER_FILE_MAP)
        self.assertIn(("the_hidden", "mark"), BANNER_FILE_MAP)
        self.assertIn(("the_slasher", "lake_mist"), BANNER_FILE_MAP)
        self.assertIn(("the_slasher", "pursuit"), BANNER_FILE_MAP)
        self.assertIn(("the_butcher", "your_heart_is_mine"), BANNER_FILE_MAP)
        self.assertIn(("veil", "through_the_veil"), BANNER_FILE_MAP)

        leap_path = resolve_banner_path("the_hidden", "leap")
        self.assertTrue(leap_path.exists(), f"Path not found: {leap_path}")

    def test_multi_slot_snapshots_and_reset(self) -> None:
        """Memastikan multi-snapshot membuat PopupBannerItem terpisah dan reset_banners bekerja."""
        snap1 = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="leap",
            ability_name="Leap",
            state=CooldownState.COOLDOWN,
            remaining_seconds=22.4,
            total_cooldown_seconds=25.0,
            progress=22.4 / 25.0,
            trigger_type="on_cast_start",
        )
        snap2 = CooldownSnapshot(
            killer_id="the_hidden",
            ability_id="mark",
            ability_name="Mark",
            state=CooldownState.READY,
            remaining_seconds=0.0,
            total_cooldown_seconds=30.0,
            progress=0.0,
            trigger_type="on_cast_start",
        )

        self.widget.show()
        self.widget.update_snapshots([snap1, snap2])
        self.assertEqual(len(self.widget._banner_items), 2)

        # Slot 0 (Leap - COOLDOWN) should be in banner_items
        slot0 = self.widget._banner_items["leap"]
        self.assertEqual(slot0.ability_id, "leap")
        self.assertFalse(slot0.isHidden())

        # Slot 1 (Mark - READY) should also be created
        slot1 = self.widget._banner_items["mark"]
        self.assertEqual(slot1.ability_id, "mark")

        # Repaint with offscreen buffer
        self.widget.repaint()

        # Trigger reset_banners
        self.widget.reset_banners()
        # Repaint after reset
        self.widget.repaint()


if __name__ == "__main__":
    unittest.main()
