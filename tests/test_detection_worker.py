"""Unit Tests for DetectionWorker Asynchronous Background Thread.

Violence District Cooldown Tracker — Week 4 (Day 19)
Verifies:
- DetectionWorker initialization and configuration setters
- Clean thread start and stop lifecycle
- Signal emission on positive detection
- Thread safety and non-blocking operation
"""

from __future__ import annotations

import time
import unittest
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QCoreApplication

from capture.capture_interface import BaseCaptureEngine, CaptureStatus, CapturedFrame
from cooldown.ability_event import AbilityEvent
from detection.detection_worker import DetectionWorker
from processing.roi_processor import ROIConfig, ROIProcessor

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MockCaptureEngine(BaseCaptureEngine):
    """Mock capture engine untuk menyuplai frame sintetis ke worker thread."""

    def __init__(self, frame: Optional[np.ndarray] = None) -> None:
        self.frame = frame or np.full((720, 1280, 3), 100, dtype=np.uint8)
        self._running = False
        self._frame_index = 0

    def start(self, target_title: str = "Roblox", target_fps: int = 30) -> bool:
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False

    def get_latest_frame(self) -> Optional[CapturedFrame]:
        if not self._running:
            return None
        self._frame_index += 1
        return CapturedFrame(
            image=self.frame.copy(),
            timestamp=time.monotonic(),
            frame_index=self._frame_index,
            width=self.frame.shape[1],
            height=self.frame.shape[0],
            latency_ms=1.5,
        )

    @property
    def current_fps(self) -> float:
        return 30.0

    @property
    def current_latency_ms(self) -> float:
        return 1.5

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> CaptureStatus:
        return CaptureStatus.RUNNING if self._running else CaptureStatus.STOPPED


class TestDetectionWorker(unittest.TestCase):
    """Test suite untuk DetectionWorker."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        self.mock_capture = MockCaptureEngine()
        self.roi_processor = ROIProcessor(ROIConfig(x=0, y=0, width=1280, height=720, enabled=False))
        self.templates_dir = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"
        self.worker = DetectionWorker(
            capture_engine=self.mock_capture,
            roi_processor=self.roi_processor,
            templates_dir=self.templates_dir,
            confidence_threshold=0.50,
        )

    def tearDown(self) -> None:
        if self.worker.isRunning():
            self.worker.stop()
        self.mock_capture.stop()

    def test_worker_initial_state(self) -> None:
        """Memastikan state awal worker terkonfigurasi dengan benar."""
        self.assertTrue(self.worker.is_enabled)
        self.assertFalse(self.worker.isRunning())

        # Test setters
        self.worker.set_enabled(False)
        self.assertFalse(self.worker.is_enabled)

        self.worker.set_confidence_threshold(0.75)
        self.assertEqual(self.worker._confidence_threshold, 0.75)

    def test_worker_lifecycle_start_stop(self) -> None:
        """Memastikan worker dapat dimulai dan dihentikan dengan bersih tanpa timeout."""
        self.mock_capture.start()
        self.worker.start()
        self.assertTrue(self.worker.isRunning())

        # Beri waktu worker berputar beberapa iterasi
        time.sleep(0.1)

        self.worker.stop()
        self.assertFalse(self.worker.isRunning())

    def test_worker_emits_event_on_synthetic_detection(self) -> None:
        """Memastikan worker memancarkan sinyal ability_detected saat frame positif terdeteksi."""
        # Ambil template acuan pertama
        loaded = self.worker.hybrid_detector.template_detector.loaded_templates
        if not loaded:
            self.skipTest("No templates loaded to run synthetic test.")

        tmpl = loaded[0]
        tw, th = tmpl["width"], tmpl["height"]

        # Buat frame sintetis yang memuat template
        synth_frame = np.full((720, 1280, 3), 40, dtype=np.uint8)
        # Tempel template di tengah frame (convert grayscale to 3 channels)
        tmpl_bgr = np.stack([tmpl["image"]] * 3, axis=-1)
        synth_frame[200 : 200 + th, 300 : 300 + tw] = tmpl_bgr

        self.mock_capture.frame = synth_frame
        self.worker.set_confidence_threshold(0.35)

        # Slot listener
        emitted_events: list[AbilityEvent] = []

        def on_detected(ev: AbilityEvent) -> None:
            emitted_events.append(ev)

        self.worker.ability_detected.connect(on_detected)

        self.mock_capture.start()
        self.worker.start()

        # Tunggu hingga beberapa frame diproses
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline and not emitted_events:
            QCoreApplication.processEvents()
            time.sleep(0.05)

        self.worker.stop()
        self.mock_capture.stop()

        self.assertGreaterEqual(len(emitted_events), 1)
        first_event = emitted_events[0]
        self.assertIsInstance(first_event, AbilityEvent)
        self.assertEqual(first_event.killer_id, "the_hidden")
        self.assertEqual(first_event.ability_id, "leap")
        self.assertEqual(first_event.source, "vision")


if __name__ == "__main__":
    unittest.main()
