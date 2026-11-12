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

from app.settings import SettingsManager, AppConfig, OverlaySettings


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
        self.assertIn(cfg.active_killer_id, ["the_hidden", "veil"])
        self.assertIsInstance(cfg.overlay, OverlaySettings)
        self.assertGreaterEqual(cfg.overlay.width, 60)
        self.assertGreaterEqual(cfg.overlay.height, 60)

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
            self.assertEqual(cfg.overlay.x, 100)
            self.assertEqual(cfg.overlay.y, 100)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_overlay_settings_defaults(self):
        """Memastikan nilai default OverlaySettings sesuai spesifikasi Day 13."""
        ovl = OverlaySettings()
        self.assertEqual(ovl.x, 100)
        self.assertEqual(ovl.y, 100)
        self.assertEqual(ovl.width, 220)
        self.assertEqual(ovl.height, 220)
        self.assertAlmostEqual(ovl.opacity, 0.95, places=2)
        self.assertTrue(ovl.visible)
        self.assertTrue(ovl.always_on_top)
        self.assertTrue(ovl.click_through)
        self.assertEqual(ovl.position, {"x": 100, "y": 100})

    def test_overlay_settings_serialization_roundtrip(self):
        """Memastikan to_dict dan from_dict mempertahankan nilai kustom secara presisi."""
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
        """Memastikan nilai invalid atau di luar batas aman ter-clamp dengan benar."""
        # Opacity > 1.0 clamped ke 1.0, width < 60 clamped ke 60, x < 0 clamped ke 0
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

        # Opacity < 0.2 clamped ke 0.2
        corrupt_min = {"opacity": 0.05}
        ovl_min = OverlaySettings.from_dict(corrupt_min)
        self.assertAlmostEqual(ovl_min.opacity, 0.2, places=2)

    def test_save_overlay_settings_preserves_roi_and_killer(self):
        """Memastikan penyimpanan pengaturan overlay tidak merusak konfigurasi ROI dan killer aktif."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)

        try:
            manager = SettingsManager(config_path=tmp_path)
            cfg = manager.load()

            # Set nilai kustom pada ROI dan Killer
            cfg.capture.roi.x = 420
            cfg.capture.roi.y = 190
            cfg.capture.roi.width = 1100
            cfg.active_killer_id = "veil"

            # Set nilai kustom pada Overlay
            cfg.overlay.x = 550
            cfg.overlay.y = 220
            cfg.overlay.visible = False
            cfg.overlay.opacity = 0.80

            # Simpan ke disk
            manager.save(cfg)

            # Muat ulang dari disk melalui instance baru
            new_manager = SettingsManager(config_path=tmp_path)
            reloaded = new_manager.load()

            # Verifikasi ROI tidak rusak
            self.assertEqual(reloaded.capture.roi.x, 420)
            self.assertEqual(reloaded.capture.roi.y, 190)
            self.assertEqual(reloaded.capture.roi.width, 1100)
            self.assertEqual(reloaded.active_killer_id, "veil")

            # Verifikasi Overlay tersimpan presisi
            self.assertEqual(reloaded.overlay.x, 550)
            self.assertEqual(reloaded.overlay.y, 220)
            self.assertFalse(reloaded.overlay.visible)
            self.assertAlmostEqual(reloaded.overlay.opacity, 0.80, places=2)
            self.assertEqual(reloaded.overlay.position, {"x": 550, "y": 220})
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
