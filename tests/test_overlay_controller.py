"""Unit & Integration Tests for OverlayController.

Week 2 — Day 11 (Cooldown Widget & Controller)
Verifies:
- Coordination between CooldownManager and OverlayWindow/CooldownWidget
- Dynamic state updates and push event listeners
- Visibility and calibration mode toggles
- Clean shutdown
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from cooldown.cooldown_manager import CooldownManager
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_state import CooldownState
from database.database_manager import AbilityConfig
from overlay.overlay_window import OverlayWindow
from overlay.overlay_controller import OverlayController


class TestOverlayController(unittest.TestCase):
    """Test suite untuk OverlayController."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.current_time = 1000.0

        def mock_clock() -> float:
            return self.current_time

        self.mock_clock = mock_clock
        self.cooldown_manager = CooldownManager(time_func=self.mock_clock)

        self.leap_ability = AbilityConfig(
            id="leap",
            name="Leap",
            cooldown_seconds=25.0,
            cooldown_verified=False,
            enabled=True,
            trigger_type="on_cast_start",
        )
        self.cooldown_manager.set_ability("the_hidden", self.leap_ability)

        self.overlay_window = OverlayWindow()
        self.controller = OverlayController(
            cooldown_manager=self.cooldown_manager,
            overlay_window=self.overlay_window,
            refresh_fps=30,
        )

    def tearDown(self) -> None:
        self.controller.close()

    def test_initial_binding_and_snapshot(self) -> None:
        """Memastikan widget terhubung dengan benar dan snapshot awal READY."""
        widget = self.controller.cooldown_widget
        self.assertIsNotNone(widget.snapshot)
        self.assertEqual(widget.snapshot.state, CooldownState.READY)
        self.assertEqual(widget.snapshot.ability_name, "Leap")

    def test_state_change_propagates_to_widget(self) -> None:
        """Memastikan pemicuan event pada CooldownManager langsung mengupdate widget."""
        event = AbilityEvent.create("the_hidden", "leap", "cast_start", timestamp=1000.0)
        self.cooldown_manager.handle_event(event)

        widget = self.controller.cooldown_widget
        self.assertEqual(widget.snapshot.state, CooldownState.COOLDOWN)
        self.assertAlmostEqual(widget.snapshot.remaining_seconds, 25.0, places=1)

    def test_visibility_controls(self) -> None:
        """Memastikan fungsi show, hide, dan toggle overlay bekerja."""
        self.controller.show_overlay()
        self.assertTrue(self.overlay_window.isVisible())
        self.assertTrue(self.controller.refresh_timer.isActive())

        self.controller.hide_overlay()
        self.assertFalse(self.overlay_window.isVisible())
        self.assertFalse(self.controller.refresh_timer.isActive())

        # Toggle
        now_visible = self.controller.toggle_overlay()
        self.assertTrue(now_visible)
        self.assertTrue(self.overlay_window.isVisible())

        now_visible = self.controller.toggle_overlay()
        self.assertFalse(now_visible)
        self.assertFalse(self.overlay_window.isVisible())

    def test_calibration_mode_toggle(self) -> None:
        """Memastikan toggle calibration mode mengatur click_through pada window."""
        # Aktifkan mode kalibrasi -> click_through harus False (agar bisa digeser)
        self.controller.set_calibration_mode(True)
        self.assertFalse(self.overlay_window.is_click_through)

        # Matikan mode kalibrasi -> click_through harus True (gameplay mode)
        self.controller.set_calibration_mode(False)
        self.assertTrue(self.overlay_window.is_click_through)

    def test_clean_shutdown(self) -> None:
        """Memastikan penutupan controller menghentikan timer dan melepas listener."""
        self.controller.start()
        self.assertTrue(self.controller.refresh_timer.isActive())

        self.controller.close()
        self.assertFalse(self.controller.refresh_timer.isActive())
        self.assertNotIn(self.controller.on_state_changed, self.cooldown_manager._listeners)


if __name__ == "__main__":
    unittest.main()
