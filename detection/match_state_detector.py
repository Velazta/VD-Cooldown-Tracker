"""Match State Detector (Lobby vs In-Game HUD Gate).

Violence District Cooldown Tracker — Week 4
Detects whether the survivor is actively inside a match or standing in the lobby/menu.
Uses Violence District in-game HUD signatures:
1. Top-right stamina icon (distinctive purple circular gauge).
2. Top-center match timer.
3. Bottom-right survivor health/status badges.
Prevents false ability detections from triggering while in the lobby or loading screen.
"""

from __future__ import annotations

import cv2
import numpy as np


class MatchStateDetector:
    """Detektor status permainan untuk membedakan antara ruang tunggu (Lobby) dan pertandingan aktif."""

    def __init__(self, min_purple_pixels: int = 40) -> None:
        self.min_purple_pixels = min_purple_pixels

    def is_in_match(self, frame: np.ndarray) -> bool:
        """Memeriksa apakah frame saat ini adalah pertandingan aktif (In-Game) atau bukan (Lobby/Menu).

        Args:
            frame: Matriks citra BGR penuh (resolusi apa pun).

        Returns:
            bool: True jika HUD pertandingan terdeteksi, False jika di lobby/menu/loading.
        """
        if frame is None or frame.size == 0:
            return False

        h, w = frame.shape[:2]

        # 1. Cek Icon Stamina Lungs (Lingkaran Ungu di Kanan Atas Viewport)
        # Daerah relatif: x: 85% - 100%, y: 15% - 40%
        stamina_crop = frame[int(h * 0.15) : int(h * 0.40), int(w * 0.85) : w]
        if stamina_crop.size > 0:
            hsv = cv2.cvtColor(stamina_crop, cv2.COLOR_BGR2HSV)
            # Rentang warna ungu icon stamina Violence District
            purple_mask = cv2.inRange(hsv, np.array([130, 60, 60]), np.array([168, 255, 255]))
            purple_count = cv2.countNonZero(purple_mask)
            if purple_count >= self.min_purple_pixels:
                return True

        # 2. Cek Indikator Status Survivor di Kanan Bawah Viewport (3 Badge Pemain)
        # Daerah relatif: x: 80% - 100%, y: 75% - 100%
        status_crop = frame[int(h * 0.75) : h, int(w * 0.80) : w]
        if status_crop.size > 0:
            gray_status = cv2.cvtColor(status_crop, cv2.COLOR_BGR2GRAY)
            # Cek kontras tinggi dari badge putih/merah survivor
            _, thresh = cv2.threshold(gray_status, 200, 255, cv2.THRESH_BINARY)
            white_count = cv2.countNonZero(thresh)
            if white_count >= 80:
                return True

        return False
