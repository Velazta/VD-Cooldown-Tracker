"""Unit Tests for MatchStateDetector (Lobby vs In-Game HUD Gate).

Violence District Cooldown Tracker — Week 4
Verifies:
- Robust detection of Violence District in-game match HUD (stamina icon, survivor badges).
- Correct rejection of lobby / main menu / blank screens.
- Graceful handling of None, empty frames, and custom resolutions.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import cv2
import numpy as np

from detection.match_state_detector import MatchStateDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestMatchStateDetector(unittest.TestCase):
    """Test suite untuk MatchStateDetector."""

    def setUp(self) -> None:
        self.detector = MatchStateDetector(min_purple_pixels=40)

    def test_empty_or_none_frame(self) -> None:
        """Frame None atau array kosong harus mengembalikan False."""
        self.assertFalse(self.detector.is_in_match(None))
        self.assertFalse(self.detector.is_in_match(np.array([], dtype=np.uint8)))

    def test_blank_lobby_frame(self) -> None:
        """Frame abu-abu polos / lobby tanpa HUD pertandingan harus False."""
        lobby_frame = np.full((720, 1280, 3), 50, dtype=np.uint8)
        self.assertFalse(self.detector.is_in_match(lobby_frame))

    def test_in_game_stamina_icon_detected(self) -> None:
        """Frame dengan icon stamina ungu khas Violence District di kanan atas harus True."""
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        h, w = frame.shape[:2]

        # Buat patch ungu di area stamina (y: 20-30%, x: 90-95%)
        # HSV ungu: H: 145 (dalam OpenCV H 0-180), S: 200, V: 200 -> BGR konversi
        purple_bgr = cv2.cvtColor(np.uint8([[[145, 200, 200]]]), cv2.COLOR_HSV2BGR)[0][0]
        y1, y2 = int(h * 0.20), int(h * 0.28)
        x1, x2 = int(w * 0.90), int(w * 0.95)
        frame[y1:y2, x1:x2] = purple_bgr

        self.assertTrue(self.detector.is_in_match(frame))

    def test_in_game_survivor_badges_detected(self) -> None:
        """Frame dengan badge survivor kontras tinggi di kanan bawah harus True."""
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        h, w = frame.shape[:2]

        # Buat patch putih di area survivor badges (y: 80-90%, x: 85-95%)
        y1, y2 = int(h * 0.82), int(h * 0.90)
        x1, x2 = int(w * 0.85), int(w * 0.92)
        frame[y1:y2, x1:x2] = (255, 255, 255)

        self.assertTrue(self.detector.is_in_match(frame))

    def test_real_photos_if_available(self) -> None:
        """Uji pada sampel foto pengguna jika tersedia di cache artifacts."""
        user_artifacts = Path(r"C:\Users\Lenovo\.gemini\antigravity\brain\40af1f6c-8f5e-4028-adc3-2c5fc22e9300\.user_uploaded")
        ingame_photo = user_artifacts / "media_1794566335864_735484ec.jpg"
        lobby_photo = user_artifacts / "media_1794566418006_6d7de380.jpg"

        if ingame_photo.exists():
            img_ingame = cv2.imread(str(ingame_photo))
            if img_ingame is not None:
                self.assertTrue(self.detector.is_in_match(img_ingame), "Foto ingame harus dideteksi True")

        if lobby_photo.exists():
            img_lobby = cv2.imread(str(lobby_photo))
            if img_lobby is not None:
                self.assertFalse(self.detector.is_in_match(img_lobby), "Foto lobby harus dideteksi False")


if __name__ == "__main__":
    unittest.main()
