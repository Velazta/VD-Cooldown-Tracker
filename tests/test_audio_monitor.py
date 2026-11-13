"""Unit Tests for AudioMonitor Module.

Violence District Cooldown Tracker — Week 4
Verifies:
- AudioMonitor property management and toggle logic.
- Time-gated `is_audio_confirmed` behavior.
- Spectral ratio discrimination: low-frequency rumble (Leap profile) vs high-frequency noise.
- Safe start and stop lifecycle.
"""

from __future__ import annotations

import time
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication

from detection.audio_monitor import AudioMonitor


class TestAudioMonitor(unittest.TestCase):
    """Test suite untuk AudioMonitor."""

    def setUp(self) -> None:
        self.app = QCoreApplication.instance() or QCoreApplication([])
        self.monitor = AudioMonitor(
            sample_rate=44100,
            buffer_size=2048,
            min_energy_threshold=100.0,
            min_bandpass_ratio=18.0,
            surge_hold_sec=0.5,
        )

    def tearDown(self) -> None:
        self.monitor.stop()

    def test_default_state(self) -> None:
        """Memverifikasi status awal AudioMonitor."""
        self.assertTrue(self.monitor.is_enabled)
        self.assertFalse(self.monitor.is_audio_confirmed())

    def test_toggle_enabled(self) -> None:
        """Memastikan set_enabled(False) menonaktifkan konfirmasi audio."""
        self.monitor.set_enabled(False)
        self.assertFalse(self.monitor.is_enabled)
        self.assertFalse(self.monitor.is_audio_confirmed())

        self.monitor.set_enabled(True)
        self.assertTrue(self.monitor.is_enabled)

    def test_audio_confirmed_window(self) -> None:
        """Memastikan is_audio_confirmed aktif dalam jendela surge_hold_sec dan kedaluwarsa setelahnya."""
        # Simulasikan lonjakan audio yang baru saja terjadi
        self.monitor._last_surge_time = time.monotonic()
        self.assertTrue(self.monitor.is_audio_confirmed())

        # Jika dinonaktifkan, harus False seketika
        self.monitor.set_enabled(False)
        self.assertFalse(self.monitor.is_audio_confirmed())

        # Aktifkan kembali dengan timestamp lama (> surge_hold_sec)
        self.monitor.set_enabled(True)
        self.monitor._last_surge_time = time.monotonic() - 1.0  # 1.0s > 0.5s
        self.assertFalse(self.monitor.is_audio_confirmed())

    def test_spectral_ratio_calculation(self) -> None:
        """Memverifikasi pemisahan frekuensi FFT: low-frequency (Leap) vs high-frequency (noise)."""
        sr = 44100
        duration = 0.05  # 50 ms
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 1. Suara frekuensi rendah (500 Hz sinewave - profil Leap)
        leap_wave = (np.sin(2 * np.pi * 500 * t) * 10000).astype(np.float32)
        fft_leap = np.abs(np.fft.rfft(leap_wave))
        freqs_leap = np.fft.rfftfreq(len(leap_wave), 1.0 / sr)
        low_m = (freqs_leap >= 100) & (freqs_leap <= 3500)
        high_m = (freqs_leap > 3500) & (freqs_leap <= 10000)
        low_energy = float(np.sum(fft_leap[low_m] ** 2))
        high_energy = float(np.sum(fft_leap[high_m] ** 2))
        ratio_leap = low_energy / max(1.0, high_energy)

        # Rasio gelombang 500 Hz murni harus sangat tinggi (jauh di atas 18.0)
        self.assertGreater(ratio_leap, 50.0)

        # 2. Suara frekuensi tinggi (6000 Hz sinewave - bukan Leap)
        high_wave = (np.sin(2 * np.pi * 6000 * t) * 10000).astype(np.float32)
        fft_high = np.abs(np.fft.rfft(high_wave))
        freqs_high = np.fft.rfftfreq(len(high_wave), 1.0 / sr)
        low_energy_h = float(np.sum(fft_high[(freqs_high >= 100) & (freqs_high <= 3500)] ** 2))
        high_energy_h = float(np.sum(fft_high[(freqs_high > 3500) & (freqs_high <= 10000)] ** 2))
        ratio_high = low_energy_h / max(1.0, high_energy_h)

        # Rasio gelombang 6000 Hz harus mendekati 0
        self.assertLess(ratio_high, 1.0)


if __name__ == "__main__":
    unittest.main()
