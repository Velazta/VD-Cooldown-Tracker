"""Unit tests for DetectorService (detection/detector_service.py)."""

import time
import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from capture.capture_interface import BaseCaptureEngine, CapturedFrame, CaptureStatus
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_bank import CooldownBank
from cooldown.cooldown_state import CooldownState
from database.database_manager import AbilityConfig, KillerConfig
from detection.detector_service import DetectorService
from processing.roi_processor import ROIConfig, ROIProcessor


class MockCaptureEngine(BaseCaptureEngine):
    def __init__(self, fps: float = 30.0) -> None:
        self._fps = fps
        self._running = False
        self._status = CaptureStatus.STOPPED
        self.dummy_frame = np.full((720, 1280, 3), 100, dtype=np.uint8)

    def start(self, target_title: str = "Roblox", target_fps: int = 30) -> bool:
        self._running = True
        self._status = CaptureStatus.CAPTURING
        return True

    def stop(self) -> None:
        self._running = False
        self._status = CaptureStatus.STOPPED

    def get_latest_frame(self) -> CapturedFrame | None:
        return CapturedFrame(
            image=self.dummy_frame,
            timestamp=time.monotonic(),
            frame_index=1,
            width=1280,
            height=720,
            latency_ms=1.0,
        )

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> CaptureStatus:
        return self._status

    @property
    def current_fps(self) -> float:
        return self._fps

    @property
    def current_latency_ms(self) -> float:
        return 1.0


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_detector_service_pipeline_end_to_end(qapp):
    mock_cap = MockCaptureEngine()
    roi_proc = ROIProcessor(ROIConfig(0, 0, 800, 400, enabled=True))

    bank = CooldownBank()
    killer_cfg = KillerConfig(
        id="the_hidden",
        name="The Hidden",
        abilities=[
            AbilityConfig(id="leap", name="Leap", cooldown_seconds=25.0, trigger_type="on_cast_start"),
            AbilityConfig(id="mark", name="Mark", cooldown_seconds=15.0, trigger_type="on_cast_start"),
        ],
    )
    bank.set_killer(killer_cfg)

    service = DetectorService(
        capture_engine=mock_cap,
        roi_processor=roi_proc,
        cooldown_bank=bank,
        target_fps=30.0,
    )

    detected_events = []
    service.ability_detected.connect(lambda ev: detected_events.append(ev))

    # Feed synthetic Leap trajectory directly through tracker & recognizers
    t0 = time.monotonic()
    for i in range(12):
        t = t0 + i * 0.033
        # Parabolic jump arc
        yc = float(4.0 * ((i * 0.033) - 0.20) ** 2 + 0.30)
        from detection.hidden_tracker import DetectionBox
        dets = [DetectionBox(0, 0.5, yc, 0.08, 0.15, 0.90)]
        service.tracker.update(dets, frame_idx=i, timestamp=t)

        history = service.tracker.get_history()
        leap_cand = service.leap_recognizer.evaluate(history)
        mark_cand = service.mark_recognizer.evaluate(history)
        evs = service.validator.process(leap_cand, mark_cand, track_age=i+1, timestamp=t, frame_idx=i)
        for ev in evs:
            service.cooldown_bank.handle_event(ev)
            service.ability_detected.emit(ev)

    # Confirm event was emitted and CooldownBank entered COOLDOWN
    assert len(detected_events) == 1
    assert detected_events[0].ability_id == "leap"
    assert bank.get_snapshot("leap").state == CooldownState.COOLDOWN
    assert bank.get_snapshot("mark").state == CooldownState.READY


def test_detector_service_clean_lifecycle(qapp):
    mock_cap = MockCaptureEngine()
    service = DetectorService(capture_engine=mock_cap, target_fps=30.0)

    service.start()
    assert service.isRunning() is True
    time.sleep(0.05)

    service.stop()
    assert service.isRunning() is False
