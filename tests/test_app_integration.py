"""Integration Tests for Main GUI Application Window.

Runs headless via PySide6 offscreen platform to verify proper binding of
SettingsManager, DatabaseManager, and Logging with GUI widgets.
"""

from __future__ import annotations

import os
import sys
import logging
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force offscreen rendering for headless CI / unit test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.settings import SettingsManager, AppConfig
from app.logger import setup_logging, APP_LOGGER_NAME
from database.database_manager import DatabaseManager
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
        self.window.close()
        self.assertFalse(self.window.render_timer.isActive())
        self.assertFalse(self.window.capture_engine.is_running)


if __name__ == "__main__":
    unittest.main()
