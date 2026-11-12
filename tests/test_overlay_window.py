"""Unit Tests for Transparent OverlayWindow.

Week 2 — Day 10 (Fondasi Jendela Overlay Transparan)
Runs headless via PySide6 offscreen platform to verify:
- Window flags (Frameless, AlwaysOnTop, DoesNotAcceptFocus)
- Translucent background and Click-through attributes
- Calibration mode drag/move signals
- Native Win32 click-through helper
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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from overlay.overlay_window import OverlayWindow, apply_native_click_through


class TestOverlayWindow(unittest.TestCase):
    """Test suite untuk verifikasi fungsionalitas OverlayWindow."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.overlay = OverlayWindow(
            x=150,
            y=250,
            width=200,
            height=200,
            opacity=0.9,
            click_through=True,
            always_on_top=True,
        )

    def tearDown(self) -> None:
        self.overlay.close()

    def test_window_flags_and_attributes(self) -> None:
        """Memastikan window flags frameless, always-on-top, dan no-focus terpasang."""
        flags = self.overlay.windowFlags()
        self.assertTrue(flags & Qt.FramelessWindowHint)
        self.assertTrue(flags & Qt.WindowStaysOnTopHint)
        self.assertTrue(flags & Qt.WindowDoesNotAcceptFocus)
        self.assertTrue(flags & Qt.WindowTransparentForInput)

        # Translucent background attribute
        self.assertTrue(self.overlay.testAttribute(Qt.WA_TranslucentBackground))
        self.assertTrue(self.overlay.testAttribute(Qt.WA_TransparentForMouseEvents))

    def test_geometry_and_opacity(self) -> None:
        """Memastikan posisi, ukuran, dan opasitas tersetel sesuai parameter."""
        self.assertEqual(self.overlay.x(), 150)
        self.assertEqual(self.overlay.y(), 250)
        self.assertEqual(self.overlay.width(), 200)
        self.assertEqual(self.overlay.height(), 200)
        self.assertAlmostEqual(self.overlay.windowOpacity(), 0.9, places=2)

    def test_toggle_click_through(self) -> None:
        """Memastikan pengubahan mode click-through mengubah atribut Qt."""
        # Nonaktifkan click-through (masuk ke mode kalibrasi)
        self.overlay.set_click_through(False)
        self.assertFalse(self.overlay.is_click_through)
        self.assertFalse(self.overlay.testAttribute(Qt.WA_TransparentForMouseEvents))
        self.assertFalse(self.overlay.windowFlags() & Qt.WindowTransparentForInput)

        # Aktifkan kembali click-through (mode gameplay)
        self.overlay.set_click_through(True)
        self.assertTrue(self.overlay.is_click_through)
        self.assertTrue(self.overlay.testAttribute(Qt.WA_TransparentForMouseEvents))
        self.assertTrue(self.overlay.windowFlags() & Qt.WindowTransparentForInput)

    def test_toggle_always_on_top(self) -> None:
        """Memastikan pengubahan always_on_top memperbarui flag jendela."""
        self.overlay.set_always_on_top(False)
        self.assertFalse(self.overlay.is_always_on_top)
        self.assertFalse(self.overlay.windowFlags() & Qt.WindowStaysOnTopHint)

        self.overlay.set_always_on_top(True)
        self.assertTrue(self.overlay.is_always_on_top)
        self.assertTrue(self.overlay.windowFlags() & Qt.WindowStaysOnTopHint)

    def test_opacity_clamping(self) -> None:
        """Memastikan nilai opasitas di luar rentang di-clamp aman antara 0.1 s/d 1.0."""
        self.overlay.set_overlay_opacity(1.5)
        self.assertAlmostEqual(self.overlay.windowOpacity(), 1.0, places=2)

        self.overlay.set_overlay_opacity(-0.5)
        self.assertAlmostEqual(self.overlay.windowOpacity(), 0.1, places=2)

    def test_position_changed_signal(self) -> None:
        """Memastikan sinyal position_changed terpancar saat posisi diubah."""
        positions: list[tuple[int, int]] = []

        def on_pos_changed(x: int, y: int) -> None:
            positions.append((x, y))

        self.overlay.position_changed.connect(on_pos_changed)
        self.overlay.set_overlay_position(300, 400)

        self.assertEqual(self.overlay.x(), 300)
        self.assertEqual(self.overlay.y(), 400)
        self.assertIn((300, 400), positions)

    def test_native_click_through_helper(self) -> None:
        """Memastikan fungsi apply_native_click_through berjalan tanpa exception."""
        hwnd = int(self.overlay.winId())
        self.assertGreater(hwnd, 0)
        res = apply_native_click_through(hwnd, True)
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
