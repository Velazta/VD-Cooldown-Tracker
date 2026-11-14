"""Unit Tests for CardPickerOverlay.

Tests:
- Initialization with DatabaseManager
- Killer card asset mapping and caching
- Carousel cycling navigation (next/prev and wrap-around)
- Selection confirmation signal emission
- Appear and dismiss animation lifecycle
- Keyboard and mouse interaction logic
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

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from database.database_manager import DatabaseManager
from overlay.card_picker_overlay import CardPickerOverlay, CARD_FILE_MAP


class TestCardPickerOverlay(unittest.TestCase):
    """Test suite for CardPickerOverlay carousel component."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.db = DatabaseManager()

    def setUp(self) -> None:
        self.picker = CardPickerOverlay(db_manager=self.db)
        self.picker.resize(1040, 290)

    def tearDown(self) -> None:
        self.picker.close()

    def test_initialization_and_killers_loaded(self) -> None:
        """Memastikan overlay memuat daftar killer lengkap dari DatabaseManager."""
        self.assertGreaterEqual(len(self.picker._killers), 7)
        self.assertEqual(self.picker.width(), 1040)
        self.assertEqual(self.picker.height(), 290)
        self.assertFalse(self.picker.isVisible())

    def test_card_assets_mapped(self) -> None:
        """Memastikan kartu-kartu yang tersedia di OVERLAY UI terpetakan."""
        self.assertIn("the_hidden", CARD_FILE_MAP)
        self.assertIn("veil", CARD_FILE_MAP)
        self.assertIn("the_abysswalker", CARD_FILE_MAP)
        self.assertIn("the_slasher", CARD_FILE_MAP)
        self.assertIn("the_butcher", CARD_FILE_MAP)
        self.assertIn("the_stalker", CARD_FILE_MAP)

        # Cek pixmap ter-cache
        self.assertIn("the_hidden", self.picker._card_pixmaps)
        hidden_pix = self.picker._card_pixmaps["the_hidden"]
        self.assertFalse(hidden_pix.isNull())

    def test_navigation_next_and_prev(self) -> None:
        """Memastikan navigasi next dan prev mengubah target index dan membungkus (wrap-around)."""
        n = len(self.picker._killers)
        self.assertEqual(self.picker._current_index, 0)

        # Geser ke kanan
        self.picker.select_next()
        self.assertEqual(self.picker._target_index, 1)

        # Geser ke kiri kembali ke 0
        self.picker.select_prev()
        self.assertEqual(self.picker._target_index, 0)

        # Geser ke kiri saat di 0 -> wrap-around ke n-1
        self.picker.select_prev()
        self.assertEqual(self.picker._target_index, n - 1)

    def test_set_active_killer(self) -> None:
        """Memastikan set_active_killer menggeser fokus ke killer yang diminta."""
        self.picker.set_active_killer("veil")
        active_killer = self.picker._killers[self.picker._current_index]
        self.assertEqual(active_killer.id, "veil")

        self.picker.set_active_killer("the_slasher")
        active_killer = self.picker._killers[self.picker._current_index]
        self.assertEqual(active_killer.id, "the_slasher")

    def test_confirm_selection_emits_signal(self) -> None:
        """Memastikan konfirmasi memancarkan killer_selected dengan ID yang benar."""
        self.picker.set_active_killer("the_butcher")

        selected_id = None

        def on_selected(kid: str) -> None:
            nonlocal selected_id
            selected_id = kid

        self.picker.killer_selected.connect(on_selected)
        self.picker.confirm_selection()

        self.assertEqual(selected_id, "the_butcher")

    def test_keyboard_events(self) -> None:
        """Memastikan event tombol panah dan enter ditangani dengan benar."""
        initial_idx = self.picker._current_index

        # Tekan Panah Kanan
        event_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        self.picker.keyPressEvent(event_right)
        self.assertEqual(self.picker._target_index, (initial_idx + 1) % len(self.picker._killers))

        # Tekan Panah Kiri
        event_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
        self.picker.keyPressEvent(event_left)
        self.assertEqual(self.picker._target_index, initial_idx)

        # Tekan Escape untuk tutup
        self.picker.show()
        event_esc = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        self.picker.keyPressEvent(event_esc)
        self.assertTrue(self.picker._is_dismissing)

    def test_repaint_does_not_crash(self) -> None:
        """Memastikan paintEvent berjalan lancar di buffer offscreen."""
        self.picker.show()
        self.picker.repaint()

        # Uji render dengan killer berbeda
        self.picker.set_active_killer("the_abysswalker")
        self.picker.repaint()

        # Uji render saat killer tanpa asset kartu PNG (procedural card)
        self.picker.set_active_killer("the_killer")
        self.picker.repaint()


if __name__ == "__main__":
    unittest.main()
