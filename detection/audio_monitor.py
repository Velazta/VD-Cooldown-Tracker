"""Real-Time Audio Loopback Spectral Monitor.

Violence District Cooldown Tracker — Week 4
Captures real-time audio from system loopback or default audio device using PySide6.QtMultimedia.
Computes rolling FFT spectral ratio (100–3,500 Hz low-band vs > 3,500 Hz high-band).
Emits audio_confirmed=True when Leap acoustic surge (ratio >= 20.0, 98.5x profile) is detected.
"""

from __future__ import annotations

import collections
import time
from typing import Deque, List, Optional

import numpy as np
from PySide6.QtCore import QIODevice, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

from app.logger import get_logger

logger = get_logger("detection.audio")


class AudioMonitor(QObject):
    """Monitor spektral audio real-time berbasis pure NumPy FFT dan QtMultimedia."""

    audio_surge_detected = Signal(float)
    """Dipancarkan saat lonjakan spektral audio Leap terdeteksi (mengirimkan timestamp)."""

    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 2048,
        min_energy_threshold: float = 400.0,
        min_bandpass_ratio: float = 18.0,
        surge_hold_sec: float = 1.2,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.min_energy_threshold = min_energy_threshold
        self.min_bandpass_ratio = min_bandpass_ratio
        self.surge_hold_sec = surge_hold_sec

        self._audio_source: Optional[QAudioSource] = None
        self._io_device: Optional[QIODevice] = None
        self._running = False
        self._enabled = True

        self._last_surge_time: float = -100.0
        self._audio_buffer: Deque[float] = collections.deque(maxlen=buffer_size)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._read_audio_stream)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._last_surge_time = -100.0
        logger.info("AudioMonitor toggled: %s", "ENABLED" if enabled else "DISABLED")

    def is_audio_confirmed(self) -> bool:
        """Memeriksa apakah lonjakan audio Leap terdeteksi dalam jendela waktu surge_hold_sec."""
        if not self._enabled:
            return False
        return (time.monotonic() - self._last_surge_time) <= self.surge_hold_sec

    def start(self) -> bool:
        """Memulai capture audio dari perangkat default atau Stereo Mix."""
        if self._running:
            return True

        try:
            device = QMediaDevices.defaultAudioInput()
            # Coba cari Stereo Mix jika tersedia untuk tangkapan game audio langsung
            for d in QMediaDevices.audioInputs():
                if "stereo mix" in d.description().lower() or "wave out" in d.description().lower():
                    device = d
                    logger.info("AudioMonitor selected loopback device: %s", d.description())
                    break

            fmt = device.preferredFormat()
            fmt.setSampleRate(self.sample_rate)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            self._audio_source = QAudioSource(device, fmt, self)
            self._audio_source.setBufferSize(self.buffer_size * 4)
            self._io_device = self._audio_source.start()

            if self._io_device is None or not self._io_device.isOpen():
                logger.warning("Could not open audio IO device for %s", device.description())
                return False

            self._running = True
            self._poll_timer.start(25)  # Poll setiap 25 ms (~40 Hz)
            logger.info("AudioMonitor started on device: %s (%d Hz)", device.description(), self.sample_rate)
            return True
        except Exception as exc:
            logger.error("Failed to start AudioMonitor: %s", exc)
            return False

    def stop(self) -> None:
        """Menghentikan capture audio secara bersih."""
        self._poll_timer.stop()
        if self._audio_source is not None:
            self._audio_source.stop()
            self._audio_source = None
        self._io_device = None
        self._running = False
        self._last_surge_time = -100.0
        logger.info("AudioMonitor stopped cleanly.")

    def _read_audio_stream(self) -> None:
        """Membaca stream audio dari buffer IO device dan menghitung FFT spektral."""
        if not self._running or self._io_device is None or not self._enabled:
            return

        bytes_avail = self._io_device.bytesAvailable()
        if bytes_avail < 512:
            return

        raw_bytes = self._io_device.read(bytes_avail)
        if not raw_bytes:
            return

        # Konversi byte stream Int16 ke NumPy array
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return

        self._audio_buffer.extend(samples.tolist())

        # Jalankan FFT jika buffer mencukupi
        if len(self._audio_buffer) >= 1024:
            buf_arr = np.array(self._audio_buffer, dtype=np.float32)
            rms_amp = float(np.sqrt(np.mean(buf_arr**2)))

            # Jika amplitude di atas noise floor
            if rms_amp >= self.min_energy_threshold:
                fft_vals = np.abs(np.fft.rfft(buf_arr))
                freqs = np.fft.rfftfreq(len(buf_arr), 1.0 / self.sample_rate)

                low_mask = (freqs >= 100) & (freqs <= 3500)
                high_mask = (freqs > 3500) & (freqs <= 10000)

                low_energy = float(np.sum(fft_vals[low_mask] ** 2))
                high_energy = float(np.sum(fft_vals[high_mask] ** 2))

                ratio = low_energy / max(1.0, high_energy)

                # Cek kriteria akustik Leap: rasio low/high >= 18.0
                if ratio >= self.min_bandpass_ratio:
                    now = time.monotonic()
                    self._last_surge_time = now
                    logger.debug("AudioMonitor: LEAP AUDIO SURGE DETECTED (ratio=%.1f, rms=%.1f)", ratio, rms_amp)
                    self.audio_surge_detected.emit(now)
