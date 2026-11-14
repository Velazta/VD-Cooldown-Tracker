"""Unit Tests for Settings Manager & Schema v2 Migration.

Violence District Cooldown Tracker — Day 6 / Manual Milestone (Phase M2)
"""

from pathlib import Path
import json
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.settings import AppConfig, ManualSettings, OverlaySettings, SettingsManager


class TestSettingsManager(unittest.TestCase):
    """Pengujian Unit untuk SettingsManager, serialisasi, dan migrasi skema v2."""

    def test_load_real_app_config(self):
        manager = SettingsManager()
        cfg = manager.load()
        self.assertIsInstance(cfg, AppConfig)
        self.assertEqual(cfg.schema_version, 2)
        self.assertEqual(cfg.capture.target_title, "Roblox")
        self.assertFalse(cfg.capture.enabled_on_start)
        self.assertGreater(cfg.capture.roi.width, 0)
        self.assertGreater(cfg.capture.roi.height, 0)
        valid_killers = [
            "the_hidden", "veil", "the_killer", "the_stalker",
            "the_abysswalker", "the_masked", "the_slasher", "the_butcher"
        ]
        self.assertIn(cfg.active_killer_id, valid_killers)
        self.assertIsInstance(cfg.overlay, OverlaySettings)
        self.assertGreaterEqual(cfg.overlay.width, 60)
        self.assertGreaterEqual(cfg.overlay.height, 60)
        self.assertIsInstance(cfg.manual, ManualSettings)
        self.assertTrue(cfg.manual.start_in_manual_mode)
        self.assertIn(cfg.manual.hotkeys["trigger_ability_1"], ["[", "Numpad1"])

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
            self.assertEqual(cfg.schema_version, 2)
            self.assertEqual(cfg.overlay.x, 24)
            self.assertEqual(cfg.overlay.y, 280)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_migration_from_v1_to_v2(self):
        """Memastikan konfigurasi v1 lama otomatis bermigrasi ke v2 tanpa kehilangan ROI/Overlay."""
        v1_payload = {
            "schema_version": 1,
            "app": {
                "name": "Violence District Cooldown Tracker",
                "version": "0.1.0-alpha",
                "debug_mode": True,
            },
            "capture": {
                "target_title": "Roblox",
                "backend": "windows_capture",
                "target_fps": 60,
                "roi": {
                    "x": 350,
                    "y": 160,
                    "width": 1200,
                    "height": 700,
                    "enabled": True,
                },
            },
            "overlay": {
                "x": 200,
                "y": 250,
                "width": 240,
                "height": 240,
                "opacity": 0.85,
                "visible": True,
            },
            "active_killer_id": "the_hidden",
        }

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            json.dump(v1_payload, tmp)
            tmp_path = Path(tmp.name)

        try:
            manager = SettingsManager(config_path=tmp_path)
            cfg = manager.load()

            # Verifikasi skema bermigrasi ke 2
            self.assertEqual(cfg.schema_version, 2)
            self.assertFalse(cfg.capture.enabled_on_start)
            self.assertTrue(cfg.manual.start_in_manual_mode)
            self.assertEqual(cfg.manual.reaction_offset, 0.0)
            self.assertEqual(cfg.manual.hotkeys["trigger_ability_1"], "Numpad1")

            # Nilai lama tetap utuh
            self.assertEqual(cfg.capture.roi.x, 350)
            self.assertEqual(cfg.overlay.x, 200)
            self.assertEqual(cfg.overlay.width, 240)

            # Verifikasi file di disk otomatis tersimpan sebagai v2
            with open(tmp_path, "r", encoding="utf-8") as f:
                saved_on_disk = json.load(f)
            self.assertEqual(saved_on_disk["schema_version"], 2)
            self.assertIn("manual", saved_on_disk)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_manual_settings_validation_and_clamping(self):
        """Memastikan nilai offset reaksi dan hotkeys divalidasi dengan aman."""
        # Offset > 2.0s di-clamp ke 2.0s; offset < 0 di-clamp ke 0.0s
        data_over = {"reaction_offset": 5.0, "hotkeys": {"trigger_ability_1": "Alt+1"}}
        man_over = ManualSettings.from_dict(data_over)
        self.assertEqual(man_over.reaction_offset, 2.0)
        self.assertEqual(man_over.hotkeys["trigger_ability_1"], "Alt+1")
        self.assertEqual(man_over.hotkeys["trigger_ability_2"], "Numpad2")  # default preserved

        data_under = {"reaction_offset": -1.5}
        man_under = ManualSettings.from_dict(data_under)
        self.assertEqual(man_under.reaction_offset, 0.0)

    def test_overlay_settings_defaults(self):
        ovl = OverlaySettings()
        self.assertEqual(ovl.x, 24)
        self.assertEqual(ovl.y, 280)
        self.assertEqual(ovl.width, 360)
        self.assertEqual(ovl.height, 360)
        self.assertAlmostEqual(ovl.opacity, 0.95, places=2)
        self.assertTrue(ovl.visible)
        self.assertTrue(ovl.always_on_top)
        self.assertTrue(ovl.click_through)
        self.assertEqual(ovl.position, {"x": 24, "y": 280})

    def test_overlay_settings_serialization_roundtrip(self):
        ovl = OverlaySettings(
            x=340,
            y=180,
            width=260,
            height=260,
            opacity=0.85,
            visible=False,
            always_on_top=True,
            click_through=False,
            fps_display=False,
        )
        data = ovl.to_dict()
        self.assertEqual(data["x"], 340)
        self.assertEqual(data["y"], 180)
        self.assertEqual(data["width"], 260)
        self.assertEqual(data["height"], 260)
        self.assertEqual(data["opacity"], 0.85)
        self.assertFalse(data["visible"])
        self.assertFalse(data["click_through"])
        self.assertEqual(data["position"], {"x": 340, "y": 180})

        restored = OverlaySettings.from_dict(data)
        self.assertEqual(restored.x, 340)
        self.assertEqual(restored.y, 180)
        self.assertEqual(restored.width, 260)
        self.assertEqual(restored.height, 260)
        self.assertAlmostEqual(restored.opacity, 0.85, places=2)
        self.assertFalse(restored.visible)
        self.assertFalse(restored.click_through)

    def test_overlay_settings_validation_and_clamping(self):
        corrupt_data = {
            "x": -50,
            "y": -100,
            "width": 10,
            "height": 99999,
            "opacity": 2.5,
            "visible": "not_bool",
        }
        ovl = OverlaySettings.from_dict(corrupt_data)
        self.assertEqual(ovl.x, 0)
        self.assertEqual(ovl.y, 0)
        self.assertEqual(ovl.width, 60)
        self.assertEqual(ovl.height, 1080)
        self.assertAlmostEqual(ovl.opacity, 1.0, places=2)

        corrupt_min = {"opacity": 0.05}
        ovl_min = OverlaySettings.from_dict(corrupt_min)
        self.assertAlmostEqual(ovl_min.opacity, 0.2, places=2)


if __name__ == "__main__":
    unittest.main()
