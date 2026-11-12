"""
Unit Tests for Settings Manager
Violence District Cooldown Tracker — Day 6 (Poin 6.3)
"""
import unittest
import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.settings import SettingsManager, AppConfig


class TestSettingsManager(unittest.TestCase):
    """Pengujian Unit untuk SettingsManager dan serialisasi AppConfig."""

    def test_load_real_app_config(self):
        manager = SettingsManager()
        cfg = manager.load()
        self.assertIsInstance(cfg, AppConfig)
        self.assertEqual(cfg.schema_version, 1)
        self.assertEqual(cfg.capture.target_title, "Roblox")
        self.assertEqual(cfg.capture.roi.width, 1280)
        self.assertEqual(cfg.capture.roi.height, 780)
        self.assertEqual(cfg.active_killer_id, "the_hidden")

    def test_fallback_on_corrupt_file(self):
        """Memastikan fallback aman ke default config jika JSON korup."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            tmp.write("{ invalid json")
            tmp_path = Path(tmp.name)

        try:
            manager = SettingsManager(config_path=tmp_path)
            cfg = manager.load()
            self.assertIsInstance(cfg, AppConfig)
            self.assertEqual(cfg.app.name, "Violence District Cooldown Tracker")
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
