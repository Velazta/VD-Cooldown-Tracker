"""Audio Spectral Profiler & Acoustic Filter Module.

Violence District Cooldown Tracker — Week 3 (Day 15 Langkah 3)
Analyzes, profiles, and compares frequency spectra of audio cues (WAV)
using pure NumPy FFT and bandpass energy ratios to distinguish Leap from Attacks/Marks.
"""

from __future__ import annotations

import argparse
import json
import math
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class SpectralProfile:
    file_name: str
    relative_path: str
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    peak_amplitude: int
    rms_energy: float
    energy_dbfs: float
    dominant_frequency_hz: float
    spectral_centroid_hz: float
    spectral_bandwidth_hz: float
    low_band_energy_pct: float  # Energi 100 - 3500 Hz (Karakteristik Leap/Vokal/Angin)
    high_band_energy_pct: float  # Energi 3500 - 10000 Hz (Karakteristik Denting/Tebasan Logam)
    band_ratio: float  # Rasio Low Band / High Band (> 1.0 indikasi vokal/leap, < 1.0 indikasi logam/attack)
    is_positive_leap: bool
    classification_prediction: str  # 'LEAP_DETECTED' atau 'ATTACK_OR_MARK'


@dataclass
class AudioInspectionReport:
    schema_version: int = 1
    total_samples_analyzed: int = 0
    leap_band_hz: Tuple[int, int] = (100, 3500)
    attack_band_hz: Tuple[int, int] = (3500, 10000)
    samples: List[SpectralProfile] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AudioInspector:
    """Inspektor dan filter spektral akustik tanpa dependensi eksternal berat."""

    def __init__(
        self,
        leap_band: Tuple[int, int] = (100, 3500),
        attack_band: Tuple[int, int] = (3500, 10000),
    ) -> None:
        self.leap_band = leap_band
        self.attack_band = attack_band

    def analyze_wav(self, file_path: Path) -> Optional[SpectralProfile]:
        """Menganalisis profil spektral lengkap dari sebuah berkas WAV."""
        try:
            with wave.open(str(file_path), "rb") as wf:
                nch = wf.getnchannels()
                rate = wf.getframerate()
                nframes = wf.getnframes()
                dur = nframes / rate if rate > 0 else 0.0
                raw_bytes = wf.readframes(nframes)

            samples = np.frombuffer(raw_bytes, dtype=np.int16)
            if len(samples) == 0:
                return None

            peak = int(np.max(np.abs(samples)))
            rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
            energy_dbfs = round(20.0 * math.log10(rms / 32767.0), 2) if rms > 0 else -96.0

            # Campur ke mono
            if nch > 1:
                mono = samples.reshape(-1, nch).mean(axis=1)
            else:
                mono = samples.astype(np.float64)

            # Hitung FFT
            fft_vals = np.abs(np.fft.rfft(mono))
            fft_freqs = np.fft.rfftfreq(len(mono), d=1.0 / rate)

            total_energy = float(np.sum(fft_vals ** 2))
            if total_energy <= 0:
                return None

            # Dominant frequency & Centroid
            dominant_freq = float(fft_freqs[np.argmax(fft_vals)])
            centroid = float(np.sum(fft_freqs * fft_vals) / np.sum(fft_vals))

            # Spectral Bandwidth
            bandwidth = float(np.sqrt(np.sum(((fft_freqs - centroid) ** 2) * fft_vals) / np.sum(fft_vals)))

            # Bandpass Energy
            low_mask = (fft_freqs >= self.leap_band[0]) & (fft_freqs < self.leap_band[1])
            high_mask = (fft_freqs >= self.attack_band[0]) & (fft_freqs < self.attack_band[1])

            low_energy = float(np.sum(fft_vals[low_mask] ** 2))
            high_energy = float(np.sum(fft_vals[high_mask] ** 2))

            low_pct = round((low_energy / total_energy) * 100.0, 2)
            high_pct = round((high_energy / total_energy) * 100.0, 2)
            ratio = round(low_energy / (high_energy + 1e-9), 2)

            is_pos = "leap" in file_path.name.lower()
            prediction = "LEAP_DETECTED" if ratio >= 1.5 and centroid < 4000.0 else "ATTACK_OR_MARK"

            return SpectralProfile(
                file_name=file_path.name,
                relative_path=str(file_path).replace("\\", "/"),
                duration_seconds=round(dur, 2),
                sample_rate_hz=rate,
                channels=nch,
                peak_amplitude=peak,
                rms_energy=round(rms, 2),
                energy_dbfs=energy_dbfs,
                dominant_frequency_hz=round(dominant_freq, 2),
                spectral_centroid_hz=round(centroid, 2),
                spectral_bandwidth_hz=round(bandwidth, 2),
                low_band_energy_pct=low_pct,
                high_band_energy_pct=high_pct,
                band_ratio=ratio,
                is_positive_leap=is_pos,
                classification_prediction=prediction,
            )
        except Exception:
            return None

    def inspect_directory(self, wav_dir: Path) -> AudioInspectionReport:
        """Memeriksa seluruh file WAV di dalam sebuah direktori."""
        report = AudioInspectionReport(
            leap_band_hz=self.leap_band,
            attack_band_hz=self.attack_band,
        )
        wav_files = sorted(wav_dir.glob("*.wav"))
        for wf in wav_files:
            profile = self.analyze_wav(wf)
            if profile is not None:
                report.samples.append(profile)

        report.total_samples_analyzed = len(report.samples)
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze audio spectra and test acoustic leap classifier.")
    parser.add_argument(
        "--dir",
        type=str,
        default="database/dataset/HIDDEN/WAV",
        help="Direktori berisi file audio WAV (default: database/dataset/HIDDEN/WAV)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/audio_inspection.json",
        help="Path berkas output JSON laporan inspeksi audio (default: dataset/audio_inspection.json)",
    )
    args = parser.parse_args()

    inspector = AudioInspector()
    report = inspector.inspect_directory(Path(args.dir))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print(" VIOLENCE DISTRICT COOLDOWN TRACKER — AUDIO SPECTRAL INSPECTION REPORT")
    print("=" * 80)
    print(f"Total File WAV Dianalisis : {report.total_samples_analyzed}")
    print(f"Pita Frekuensi Leap (Low) : {report.leap_band_hz[0]} - {report.leap_band_hz[1]} Hz")
    print(f"Pita Frekuensi Attack/Mark: {report.attack_band_hz[0]} - {report.attack_band_hz[1]} Hz")
    print("-" * 80)
    print(f"{'Nama Berkas':<32} | {'Centroid':<11} | {'Low%':<6} | {'High%':<6} | {'Rasio':<6} | {'Prediksi'}")
    print("-" * 80)

    for s in report.samples:
        gt = "[LEAP]" if s.is_positive_leap else "[NEG] "
        print(
            f"{gt} {s.file_name:<26} | {s.spectral_centroid_hz:7.1f} Hz | "
            f"{s.low_band_energy_pct:5.1f}% | {s.high_band_energy_pct:5.1f}% | "
            f"{s.band_ratio:5.2f}x | {s.classification_prediction}"
        )

    print("=" * 80)
    print(f"Laporan JSON disimpan ke: {out_path.resolve()}")


if __name__ == "__main__":
    main()
