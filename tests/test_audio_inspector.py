"""Unit and Integration Tests for Audio Inspector Module.

Violence District Cooldown Tracker — Week 3 (Day 15 Langkah 3)
Verifies:
- Accurate extraction of audio spectral metrics (centroid, dominant frequency, dBFS)
- Bandpass energy ratio calculation (Low vs High frequency bands)
- Reliable acoustic classification separating Leap from Attacks/Marks
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from tools.audio_inspector import AudioInspector, SpectralProfile, AudioInspectionReport

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestAudioInspector(unittest.TestCase):
    """Test suite untuk AudioInspector."""

    def setUp(self) -> None:
        self.inspector = AudioInspector()
        self.wav_dir = PROJECT_ROOT / "database" / "dataset" / "HIDDEN" / "WAV"

    def test_inspect_leap_audio_cue(self) -> None:
        """Memastikan suara Leap memiliki energi vokal/angin dominan di bawah 3500 Hz."""
        leap_wav = self.wav_dir / "hidden_leap_var1.wav"
        self.assertTrue(leap_wav.exists())

        profile = self.inspector.analyze_wav(leap_wav)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.channels, 2)
        self.assertEqual(profile.sample_rate_hz, 44100)
        self.assertTrue(profile.is_positive_leap)

        # Verifikasi karakteristik spektral vokal/grunt
        self.assertLess(profile.spectral_centroid_hz, 3500.0)
        self.assertGreater(profile.low_band_energy_pct, 85.0)
        self.assertLess(profile.high_band_energy_pct, 5.0)
        self.assertGreater(profile.band_ratio, 20.0)
        self.assertEqual(profile.classification_prediction, "LEAP_DETECTED")

    def test_inspect_negative_attack_cues(self) -> None:
        """Memastikan suara serangan pisau dan tombak memiliki energi frekuensi tinggi dan centroid > 5000 Hz."""
        negative_files = [
            "hidden_basic_attack.wav",
            "hidden_mark_hit_wall.wav",
            "hidden_mark_no_hit_survivor.wav",
            "mark_hit_survivor.wav",
        ]

        for fname in negative_files:
            wav_path = self.wav_dir / fname
            profile = self.inspector.analyze_wav(wav_path)
            self.assertIsNotNone(profile)
            self.assertFalse(profile.is_positive_leap)
            self.assertGreater(profile.spectral_centroid_hz, 5000.0)
            self.assertEqual(profile.classification_prediction, "ATTACK_OR_MARK")

    def test_inspect_directory_and_report_serialization(self) -> None:
        """Memverifikasi inspeksi direktori penuh dan serialisasi laporan JSON."""
        report = self.inspector.inspect_directory(self.wav_dir)
        self.assertEqual(report.total_samples_analyzed, 5)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_audio_report.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)

            self.assertTrue(out_file.exists())
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(data["total_samples_analyzed"], 5)
            self.assertEqual(len(data["samples"]), 5)


if __name__ == "__main__":
    unittest.main()
