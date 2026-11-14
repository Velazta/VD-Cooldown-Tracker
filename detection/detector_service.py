"""End-to-End Detector Service & Pipeline Orchestrator.

Violence District Cooldown Tracker — Rebuild Phase 5 (Task 5.3)
Asynchronously connects:
Frame Capture -> ROI Processor -> YOLO Entity Detector (ONNX/Torch) ->
HiddenTracker -> LeapRecognizer & MarkRecognizer -> EventValidator ->
CooldownBank -> UI Overlay Signal.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from app.logger import get_logger
from capture.capture_interface import BaseCaptureEngine, CapturedFrame
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_bank import CooldownBank
from detection.event_validator import EventValidator
from detection.hidden_tracker import DetectionBox, HiddenTracker
from detection.leap_recognizer import LeapRecognizer
from detection.mark_recognizer import MarkRecognizer
from processing.roi_processor import ROIProcessor

logger = get_logger("detection.service")


class DetectorService(QThread):
    ability_detected = Signal(object)      # Emits AbilityEvent
    target_tracked = Signal(dict)          # Emits tracking telemetry for GUI HUD
    telemetry_updated = Signal(dict)       # Periodic performance telemetry
    service_error = Signal(str)

    def __init__(
        self,
        capture_engine: BaseCaptureEngine,
        roi_processor: Optional[ROIProcessor] = None,
        cooldown_bank: Optional[CooldownBank] = None,
        model_path: Optional[Path] = None,
        conf_threshold: float = 0.25,
        target_fps: float = 60.0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.capture_engine = capture_engine
        self.roi_processor = roi_processor or ROIProcessor()
        self.cooldown_bank = cooldown_bank or CooldownBank()
        self.conf_threshold = conf_threshold
        self.target_fps = target_fps
        self._is_running: bool = False

        # Neural detector
        self.model_path = model_path
        self._net: Optional[Any] = None
        self._init_detector()

        # Phase 4 & 5 Modules
        self.tracker = HiddenTracker(max_hold_frames=6, ema_alpha=0.65)
        self.leap_recognizer = LeapRecognizer(min_points=6, min_r2=0.50, require_airborne_apex=True)
        self.mark_recognizer = MarkRecognizer(min_area_growth=1.20, max_vertical_span=0.030)
        self.validator = EventValidator()

        # Telemetry
        self.total_frames_processed: int = 0
        self.fps_actual: float = 0.0

    def _init_detector(self) -> None:
        if self.model_path and Path(self.model_path).exists():
            p_str = str(self.model_path)
            try:
                if p_str.endswith(".onnx"):
                    self._net = cv2.dnn.readNetFromONNX(p_str)
                    self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    logger.info("Loaded ONNX detector: %s", p_str)
                else:
                    from ultralytics import YOLO
                    self._net = YOLO(p_str)
                    logger.info("Loaded PyTorch detector: %s", p_str)
            except Exception as e:
                logger.error("Failed to load detector model: %s", e)
                self._net = None

    def run(self) -> None:
        self._is_running = True
        logger.info("DetectorService thread started at target %s FPS.", self.target_fps)
        last_time = time.monotonic()
        frame_idx = 0

        while self._is_running:
            loop_start = time.monotonic()
            frame = self.capture_engine.get_latest_frame()

            if frame is not None and frame.image is not None and frame.image.size > 0:
                frame_idx += 1
                self.total_frames_processed += 1
                self._process_single_frame(frame.image, frame_idx, frame.timestamp)

            # Frame rate pacing
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.001, (1.0 / self.target_fps) - elapsed)
            time.sleep(sleep_time)

            now = time.monotonic()
            if now - last_time >= 1.0:
                self.fps_actual = self.total_frames_processed / max(1e-3, (now - last_time))
                self.total_frames_processed = 0
                last_time = now
                self.telemetry_updated.emit({
                    "fps": round(self.fps_actual, 1),
                    "is_tracking": self.tracker.is_active,
                    "lost_frames": self.tracker.lost_frames,
                })

        logger.info("DetectorService thread terminated.")

    def _process_single_frame(self, frame_bgr: np.ndarray, frame_idx: int, timestamp: float) -> None:
        cropped = self.roi_processor.crop(frame_bgr)
        if cropped is None or cropped.size == 0:
            return

        ch, cw = cropped.shape[:2]
        detections: List[DetectionBox] = []

        # 1. Run neural inference if model loaded
        if self._net is not None:
            detections = self._infer(cropped, cw, ch)

        # 2. Update entity tracker
        track_state = self.tracker.update(detections, frame_idx, timestamp)
        track_age = len(self.tracker.history)

        leap_cand = None
        mark_cand = None

        if track_state is not None:
            self.target_tracked.emit({
                "xc": track_state.xc,
                "yc": track_state.yc,
                "w": track_state.w,
                "h": track_state.h,
                "is_holding": track_state.is_holding,
                "track_age": track_age,
            })

            # 3. Action Recognition (Leap & Mark)
            history = self.tracker.get_history()
            leap_cand = self.leap_recognizer.evaluate(history)
            mark_cand = self.mark_recognizer.evaluate(history)

        # 4. Multi-Frame Event Validation & Confirmation
        events = self.validator.process(leap_cand, mark_cand, track_age, timestamp, frame_idx)

        # 5. Route confirmed events to CooldownBank & UI
        for ev in events:
            logger.info("ACTION CONFIRMED: %s (source: %s, conf: %s)", ev.ability_id, ev.source, ev.confidence)
            self.cooldown_bank.handle_event(ev)
            self.ability_detected.emit(ev)

    def _infer(self, cropped: np.ndarray, cw: int, ch: int) -> List[DetectionBox]:
        boxes: List[DetectionBox] = []
        if isinstance(self._net, cv2.dnn.Net):
            # ONNX inference via cv2.dnn
            blob = cv2.dnn.blobFromImage(cropped, 1.0 / 255.0, (640, 640), swapRB=True, crop=False)
            self._net.setInput(blob)
            out = self._net.forward()
            # Parse YOLOv8 output shape: [1, 6, 8400] -> [xc, yc, w, h, cls0, cls1]
            out = np.squeeze(out, axis=0)  # [6, 8400]
            if out.shape[0] == 6 and out.shape[1] > 6:
                out = out.T  # [8400, 6]
            for row in out:
                scores = row[4:]
                cls_id = int(np.argmax(scores))
                conf = float(scores[cls_id])
                if conf >= self.conf_threshold:
                    xc, yc, bw, bh = row[0] / 640.0, row[1] / 640.0, row[2] / 640.0, row[3] / 640.0
                    boxes.append(DetectionBox(cls_id, xc, yc, bw, bh, conf))
        else:
            # Ultralytics model
            res = self._net.predict(cropped, conf=self.conf_threshold, imgsz=640, verbose=False)
            if res and res[0].boxes:
                for b in res[0].boxes:
                    cid = int(b.cls[0].item())
                    conf = float(b.conf[0].item())
                    xywhn = b.xywhn[0].cpu().numpy()
                    boxes.append(DetectionBox(cid, float(xywhn[0]), float(xywhn[1]), float(xywhn[2]), float(xywhn[3]), conf))
        return boxes

    def stop(self) -> None:
        self._is_running = False
        self.wait(2000)
