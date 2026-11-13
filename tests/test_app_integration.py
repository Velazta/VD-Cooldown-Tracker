"""Integration Tests for Main GUI Application Window.

Runs headless via PySide6 offscreen platform to verify proper binding of
SettingsManager, DatabaseManager, and Logging with GUI widgets.
"""

from __future__ import annotations

import os
import sys
import logging
import tempfile
import time
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force offscreen rendering for headless CI / unit test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from app.settings import SettingsManager, AppConfig
from app.logger import setup_logging, APP_LOGGER_NAME
from database.database_manager import DatabaseManager
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_state import CooldownState
from main import CapturePreviewWindow


class TestMainAppIntegration(unittest.TestCase):
    """End-to-End GUI Integration Test Suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_app_config.json"
        self.log_path = Path(self.temp_dir.name) / "test_gui.log"

        setup_logging(debug_mode=True, log_file=self.log_path)

        self.settings_mgr = SettingsManager(self.config_path)
        # Real database path for testing
        self.db_mgr = DatabaseManager(PROJECT_ROOT / "database" / "killerDatabase.json")

        self.window = CapturePreviewWindow(
            settings_manager=self.settings_mgr,
            db_manager=self.db_mgr,
        )

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        # Close file handlers to release Windows file lock on test_gui.log
        logger = logging.getLogger(APP_LOGGER_NAME)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        self.temp_dir.cleanup()

    def test_window_initialization_bindings(self) -> None:
        """Verify window properly reflects data loaded from settings and database."""
        # 1. Title verification
        self.assertIn("Violence District Cooldown Tracker", self.window.windowTitle())
        self.assertIn("Day 7", self.window.windowTitle())

        # 2. Target window binding
        self.assertEqual(self.window.target_input.text(), "Roblox")

        # 3. ROI SpinBoxes binding
        roi = self.settings_mgr.config.capture.roi
        self.assertEqual(self.window.spin_x.value(), roi.x)
        self.assertEqual(self.window.spin_y.value(), roi.y)
        self.assertEqual(self.window.spin_w.value(), roi.width)
        self.assertEqual(self.window.spin_h.value(), roi.height)

        # 4. Killer Combobox populated
        self.assertGreaterEqual(self.window.combo_killer.count(), 2)
        items = [self.window.combo_killer.itemText(i) for i in range(self.window.combo_killer.count())]
        self.assertIn("The Hidden", items)
        self.assertIn("Veil", items)

    def test_change_active_killer_updates_config(self) -> None:
        """Verify selecting a different killer in the combobox updates and persists config."""
        # Find index for Veil
        veil_idx = -1
        for i in range(self.window.combo_killer.count()):
            if self.window.combo_killer.itemData(i) == "veil":
                veil_idx = i
                break

        self.assertNotEqual(veil_idx, -1)
        self.window.combo_killer.setCurrentIndex(veil_idx)

        # Verify active killer updated in settings manager
        self.assertEqual(self.settings_mgr.config.active_killer_id, "veil")

        # Verify ability display updated with Veil's ability
        abilities_text = self.window.abilities_container.text()
        self.assertIn("Through The Veil", abilities_text)
        self.assertIn("20.0s", abilities_text)

    def test_save_roi_config_persists_changes(self) -> None:
        """Verify changing spinbox and clicking save persists coordinates."""
        self.window.spin_x.setValue(400)
        self.window.spin_y.setValue(200)
        self.window.spin_w.setValue(1100)
        self.window.spin_h.setValue(700)

        # Call save
        self.window.config.capture.roi = self.window.roi_config
        self.settings_mgr.save(self.window.config)

        # Reload from disk and verify
        reloaded = SettingsManager(self.config_path).config
        self.assertEqual(reloaded.capture.roi.x, 400)
        self.assertEqual(reloaded.capture.roi.y, 200)
        self.assertEqual(reloaded.capture.roi.width, 1100)
        self.assertEqual(reloaded.capture.roi.height, 700)

    def test_clean_close_event(self) -> None:
        """Verify closeEvent stops render timer and cleanly releases capture engine."""
        self.assertTrue(self.window.render_timer.isActive())
        self.assertTrue(self.window.overlay_controller.refresh_timer.isActive())
        self.window.close()
        self.assertFalse(self.window.render_timer.isActive())
        self.assertFalse(self.window.overlay_controller.refresh_timer.isActive())
        self.assertFalse(self.window.capture_engine.is_running)

    def test_ability_combobox_and_cooldown_manager_sync(self) -> None:
        """Verify ability selector reflects active killer abilities and syncs to CooldownManager."""
        # 1. By default, active killer is the_hidden (or first killer)
        self.assertGreaterEqual(self.window.combo_ability.count(), 1)
        active_ability = self.window.cooldown_manager.ability
        self.assertIsNotNone(active_ability)
        self.assertEqual(active_ability.id, "leap")

        # 2. Switch ability within same killer to 'mark' if available
        mark_idx = -1
        for i in range(self.window.combo_ability.count()):
            if self.window.combo_ability.itemData(i) == "mark":
                mark_idx = i
                break
        if mark_idx != -1:
            self.window.combo_ability.setCurrentIndex(mark_idx)
            self.assertEqual(self.window.cooldown_manager.ability.id, "mark")

        # 3. Switch killer to 'veil'
        veil_idx = -1
        for i in range(self.window.combo_killer.count()):
            if self.window.combo_killer.itemData(i) == "veil":
                veil_idx = i
                break
        self.assertNotEqual(veil_idx, -1)
        self.window.combo_killer.setCurrentIndex(veil_idx)

        # Ability selector should automatically reload with Veil's abilities
        self.assertEqual(self.window.cooldown_manager.killer_id, "veil")
        self.assertEqual(self.window.cooldown_manager.ability.id, "through_the_veil")
        self.assertEqual(self.window.cooldown_manager.ability.trigger_type, "on_release")

    def test_manual_simulate_cast_start_and_reset(self) -> None:
        """Verify simulate_cast_start initiates cooldown on Leap and reset returns to READY."""
        # Ensure active is The Hidden / Leap (on_cast_start)
        the_hidden_idx = -1
        for i in range(self.window.combo_killer.count()):
            if self.window.combo_killer.itemData(i) == "the_hidden":
                the_hidden_idx = i
                break
        if the_hidden_idx != -1:
            self.window.combo_killer.setCurrentIndex(the_hidden_idx)

        leap_idx = -1
        for i in range(self.window.combo_ability.count()):
            if self.window.combo_ability.itemData(i) == "leap":
                leap_idx = i
                break
        if leap_idx != -1:
            self.window.combo_ability.setCurrentIndex(leap_idx)

        # Initially READY
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.READY)

        # Simulate Cast Start
        self.window.simulate_cast_start(source="manual")
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.COOLDOWN)
        self.assertGreater(self.window.cooldown_manager.get_snapshot().remaining_seconds, 0.0)

        # Reset Cooldown
        self.window.reset_cooldown()
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.READY)
        self.assertEqual(self.window.cooldown_manager.get_snapshot().remaining_seconds, 0.0)

    def test_manual_simulate_on_release_ability(self) -> None:
        """Verify on_release ability (Veil) transitions to WAITING_FOR_RELEASE then COOLDOWN."""
        # Switch to Veil
        veil_idx = -1
        for i in range(self.window.combo_killer.count()):
            if self.window.combo_killer.itemData(i) == "veil":
                veil_idx = i
                break
        self.assertNotEqual(veil_idx, -1)
        self.window.combo_killer.setCurrentIndex(veil_idx)

        self.assertEqual(self.window.cooldown_manager.state, CooldownState.READY)

        # Cast Start enters stance
        self.window.simulate_cast_start(source="manual")
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.WAITING_FOR_RELEASE)

        # Release triggers cooldown
        self.window.simulate_release(source="manual")
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.COOLDOWN)
        self.assertGreater(self.window.cooldown_manager.get_snapshot().remaining_seconds, 0.0)

        # Reset
        self.window.reset_cooldown()
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.READY)

    def test_hotkey_key_press_events(self) -> None:
        """Verify F1 (cast), F2 (release), F3 (reset), and F4 (toggle overlay) hotkeys."""
        # Switch to Veil to test both F1 and F2
        veil_idx = -1
        for i in range(self.window.combo_killer.count()):
            if self.window.combo_killer.itemData(i) == "veil":
                veil_idx = i
                break
        self.assertNotEqual(veil_idx, -1)
        self.window.combo_killer.setCurrentIndex(veil_idx)

        # F1: Cast Start
        event_f1 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier)
        self.window.keyPressEvent(event_f1)
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.WAITING_FOR_RELEASE)

        # F2: Release
        event_f2 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier)
        self.window.keyPressEvent(event_f2)
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.COOLDOWN)

        # F3: Reset
        event_f3 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F3, Qt.KeyboardModifier.NoModifier)
        self.window.keyPressEvent(event_f3)
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.READY)

        # F4: Toggle Overlay
        init_vis = self.window.overlay_window.isVisible()
        event_f4 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F4, Qt.KeyboardModifier.NoModifier)
        self.window.keyPressEvent(event_f4)
        self.assertNotEqual(self.window.overlay_window.isVisible(), init_vis)

    def test_overlay_visibility_and_calibration_checkboxes(self) -> None:
        """Verify UI checkboxes control overlay visibility and calibration mode."""
        # 1. Overlay Visibility checkbox
        self.window.check_overlay_visible.setChecked(False)
        self.assertFalse(self.window.overlay_window.isVisible())

        self.window.check_overlay_visible.setChecked(True)
        self.assertTrue(self.window.overlay_window.isVisible())

        # 2. Calibration Mode checkbox (disables click-through so user can drag)
        self.window.check_calibration_mode.setChecked(True)
        self.assertFalse(self.window.overlay_window.is_click_through)

        self.window.check_calibration_mode.setChecked(False)
        self.assertTrue(self.window.overlay_window.is_click_through)

    def test_hotkey_not_blocked_when_combobox_focused(self) -> None:
        """Verify F4 toggles overlay via eventFilter even when QComboBox has focus."""
        self.window.combo_killer.setFocus()
        init_vis = self.window.overlay_window.isVisible()

        # Send KeyPress F4 to combo_killer via QApplication
        event_f4 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F4, Qt.KeyboardModifier.NoModifier)
        self.app.notify(self.window.combo_killer, event_f4)

        # Overlay visibility must have toggled, and combo popup must NOT be open
        self.assertNotEqual(self.window.overlay_window.isVisible(), init_vis)
        self.assertFalse(self.window.combo_killer.view().isVisible())

    def test_overlay_position_persistence_lifecycle(self) -> None:
        """Verify overlay position changes persist to disk and restore on window restart."""
        # 1. Simulate dragging overlay to a new position
        self.window.overlay_window.move(480, 240)
        self.window.on_overlay_moved(480, 240)
        self.assertEqual(self.settings_mgr.config.overlay.x, 480)
        self.assertEqual(self.settings_mgr.config.overlay.y, 240)

        # 2. Close current window
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

        # 3. Instantiate a second window using the same settings manager (reloaded from disk)
        reloaded_settings = SettingsManager(self.config_path)
        second_window = CapturePreviewWindow(
            settings_manager=reloaded_settings,
            db_manager=self.db_mgr,
        )

        try:
            self.assertEqual(second_window.overlay_window.x(), 480)
            self.assertEqual(second_window.overlay_window.y(), 240)
            self.assertEqual(second_window.config.overlay.x, 480)
            self.assertEqual(second_window.config.overlay.y, 240)
        finally:
            second_window.close()
            second_window.deleteLater()
            self.app.processEvents()

    def test_clean_shutdown_under_active_cooldown(self) -> None:
        """Verify closing the application while a cooldown is actively running exits cleanly."""
        self.window.simulate_cast_start(source="manual")
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.COOLDOWN)
        self.assertTrue(self.window.overlay_controller.refresh_timer.isActive())

        # Close during countdown
        self.window.close()
        self.assertFalse(self.window.render_timer.isActive())
        self.assertFalse(self.window.overlay_controller.refresh_timer.isActive())
        self.assertFalse(self.window.capture_engine.is_running)

    def test_auto_detection_integration_wiring(self) -> None:
        """Verify DetectionWorker integration into main GUI window and auto-cooldown trigger."""
        self.assertTrue(hasattr(self.window, "detection_worker"))
        self.assertTrue(self.window.check_auto_detect.isChecked())
        self.assertTrue(self.window.detection_worker.is_enabled)

        # Toggle auto-detection off
        self.window.check_auto_detect.setChecked(False)
        self.assertFalse(self.window.detection_worker.is_enabled)
        self.assertIn("DISABLED", self.window.detector_badge.text())

        # Toggle auto-detection on
        self.window.check_auto_detect.setChecked(True)
        self.assertTrue(self.window.detection_worker.is_enabled)

        # Test simulated auto-detection event arrival
        event = AbilityEvent(
            killer_id="the_hidden",
            ability_id="leap",
            event_type="cast_start",
            timestamp=time.monotonic(),
            confidence=0.89,
            source="vision",
        )
        self.window.on_auto_ability_detected(event)

        # Verify CooldownManager transitioned into COOLDOWN state
        self.assertEqual(self.window.cooldown_manager.state, CooldownState.COOLDOWN)
        self.assertIn("LEAP DETECTED", self.window.detector_badge.text())


if __name__ == "__main__":
    unittest.main()
