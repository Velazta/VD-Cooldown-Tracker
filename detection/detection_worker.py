"""Asynchronous Background Detection Worker Thread.

Violence District Cooldown Tracker — Week 4 (Day 19)
Consumes live frames from BaseCaptureEngine without blocking the PySide6 UI thread.
Runs HybridDetector (multi-scale template matching + parabolic motion tracking)
and emits normalized AbilityEvent signals to CooldownManager upon verified action.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from app.logger import get_logger
from capture.capture_interface import BaseCaptureEngine, CapturedFrame
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_manager import CooldownManager
from cooldown.cooldown_state import CooldownState
from detection.hybrid_detector import HybridDetectionEvaluation, HybridDetector
from detection.match_state_detector import MatchStateDetector
from detection.trajectory_action_detector import ActionRecognitionResult, TrajectoryActionDetector
from detection.yolo_detector import YoloDetectionResult, YoloDetector
from processing.roi_processor import ROIProcessor

logger = get_logger("detection.worker")


class DetectionWorker(QThread):
    """Background worker thread yang mengeksekusi pipeline visi komputer secara asynchronous."""

    ability_detected = Signal(object)
    """Dipancarkan saat kemampuan Killer terdeteksi valid. Mengirimkan objek AbilityEvent."""

    target_tracked = Signal(dict)
    """Dipancarkan real-time saat target visual terdeteksi/terlacak di dalam ROI."""

    telemetry_updated = Signal(dict)
    """Dipancarkan secara periodik untuk memperbarui telemetri detektor di GUI."""

    worker_error = Signal(str)
    """Dipancarkan jika terjadi exception yang tidak tertangani di dalam loop."""

    def __init__(
        self,
        capture_engine: BaseCaptureEngine,
        roi_processor: Optional[ROIProcessor] = None,
        cooldown_manager: Optional[CooldownManager] = None,
        templates_dir: Optional[Path] = None,
        confidence_threshold: float = 0.54,
        yolo_model_path: Optional[Path] = None,
        detector_backend: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.capture_engine = capture_engine
        self.roi_processor = roi_processor or ROIProcessor()
        self.cooldown_manager = cooldown_manager

        # Inisialisasi HybridDetector multi-modal (Week 4 baseline)
        t_dir = templates_dir or (Path(__file__).resolve().parent.parent / "dataset" / "templates" / "the_hidden")
        self.hybrid_detector = HybridDetector(
            templates_dir=t_dir,
            template_threshold=confidence_threshold,
            min_motion_span_px=80.0,
            debounce_sec=15.0,
        )

        # Inisialisasi YoloDetector neural network dan TrajectoryActionDetector (Week 5)
        default_yolo_path = Path(__file__).resolve().parent.parent / "models" / "the_hidden_yolov8n.onnx"
        actual_yolo_path = yolo_model_path or default_yolo_path
        self.yolo_detector = YoloDetector(
            model_path=actual_yolo_path if actual_yolo_path.exists() else None,
            confidence_threshold=confidence_threshold,
        )
        self.trajectory_action_detector = TrajectoryActionDetector(
            velocity_threshold_px_s=-180.0,
            elevation_threshold_px=35.0,
            debounce_seconds=15.0,
        )

        # Pemilihan backend deteksi otomatis
        if detector_backend is not None:
            self._detector_backend = detector_backend
        elif yolo_model_path is not None and yolo_model_path.exists():
            self._detector_backend = "yolo"
        elif templates_dir is not None:
            self._detector_backend = "hybrid"
        elif default_yolo_path.exists():
            self._detector_backend = "yolo"
        else:
            self._detector_backend = "hybrid"

        logger.info("DetectionWorker initialized with backend: %s", self._detector_backend.upper())

        self.match_detector = MatchStateDetector()
        self._filter_match_state = True

        self._running = False
        self._enabled = True
        self._audio_confirmed = False
        self._confidence_threshold = confidence_threshold

        # Telemetry tracking
        self._last_processed_frame_index = -1
        self._frames_processed = 0
        self._fps_start_time = time.monotonic()
        self._current_fps = 0.0
        self._last_latency_ms = 0.0

    @property
    def detector_backend(self) -> str:
        return self._detector_backend

    def set_backend(self, backend: str) -> None:
        """Mengubah backend detektor visual ('yolo' atau 'hybrid')."""
        if backend in ("yolo", "hybrid"):
            self._detector_backend = backend
            logger.info("DetectionWorker backend changed to: %s", backend.upper())

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Mengaktifkan atau menonaktifkan proses inferensi deteksi."""
        self._enabled = enabled
        logger.info("DetectionWorker auto-detection toggled: %s", "ENABLED" if enabled else "DISABLED")

    def set_confidence_threshold(self, threshold: float) -> None:
        """Mengubah ambang batas keyakinan deteksi visual secara dinamis."""
        self._confidence_threshold = max(0.10, min(0.95, threshold))
        self.hybrid_detector.template_detector.confidence_threshold = self._confidence_threshold
        self.yolo_detector.confidence_threshold = self._confidence_threshold
        logger.info("DetectionWorker confidence threshold updated to: %.2f", self._confidence_threshold)

    def set_audio_confirmed(self, confirmed: bool) -> None:
        """Menyetel status konfirmasi audio (disuplai oleh loopback audio capture)."""
        self._audio_confirmed = confirmed

    def set_filter_match_state(self, enabled: bool) -> None:
        """Mengatur apakah detektor hanya aktif saat mendeteksi HUD pertandingan (bukan di lobby)."""
        self._filter_match_state = enabled
        logger.info("DetectionWorker match-state filter toggled: %s", "ENABLED" if enabled else "DISABLED")

    def set_cooldown_manager(self, cooldown_manager: CooldownManager) -> None:
        """Mengatur referensi CooldownManager untuk mencegah pemicuan ulang saat cooldown aktif."""
        self.cooldown_manager = cooldown_manager

    def set_roi_processor(self, roi_processor: ROIProcessor) -> None:
        """Memperbarui processor ROI saat koordinat diubah pengguna."""
        self.roi_processor = roi_processor

    def stop(self) -> None:
        """Menghentikan worker thread secara aman dan bersih."""
        self._running = False
        self.requestInterruption()
        if self.isRunning():
            self.wait(1000)
        logger.info("DetectionWorker stopped cleanly.")

    def run(self) -> None:
        """Loop utama pemrosesan citra pada background thread."""
        self._running = True
        self._frames_processed = 0
        self._fps_start_time = time.monotonic()
        logger.info("DetectionWorker thread started execution.")

        while self._running and not self.isInterruptionRequested():
            try:
                # 1. Jika auto-detection dinonaktifkan, tidur sejenak agar hemat CPU
                if not self._enabled:
                    time.sleep(0.05)
                    continue

                # 2. Ambil frame terbaru dari buffer capture
                captured: Optional[CapturedFrame] = self.capture_engine.get_latest_frame()
                if captured is None or captured.image is None or captured.image.size == 0:
                    time.sleep(0.01)
                    continue

                # Hindari memproses frame yang sama berulang kali
                if captured.frame_index == self._last_processed_frame_index:
                    time.sleep(0.008)
                    continue

                self._last_processed_frame_index = captured.frame_index

                # 3. Cek apakah kemampuan sedang dalam masa cooldown aktif (cegah infinite loopback)
                if self.cooldown_manager is not None and self.cooldown_manager.state == CooldownState.COOLDOWN:
                    time.sleep(0.04)
                    self.telemetry_updated.emit(
                        {
                            "state": "COOLDOWN_ACTIVE",
                            "is_detected": False,
                            "confidence": 0.0,
                            "template_score": 0.0,
                            "motion_span_px": 0.0,
                            "latency_ms": 0.0,
                            "worker_fps": round(self._current_fps, 1),
                            "fusion_strategy": "COOLDOWN_LOCKOUT",
                        }
                    )
                    continue

                # 4. Cek apakah survivor sedang berada di dalam match (cegah pemicuan di lobby/menu)
                if self._filter_match_state and not self.match_detector.is_in_match(captured.image):
                    time.sleep(0.04)
                    self.telemetry_updated.emit(
                        {
                            "state": "LOBBY_STANDBY",
                            "is_detected": False,
                            "confidence": 0.0,
                            "template_score": 0.0,
                            "motion_span_px": 0.0,
                            "latency_ms": 0.0,
                            "worker_fps": round(self._current_fps, 1),
                            "fusion_strategy": "LOBBY_GATE",
                        }
                    )
                    continue

                # 5. Potong frame berdasarkan ROI aktif jika tersedia
                frame_to_process = captured.image
                if self.roi_processor is not None and self.roi_processor.config.enabled:
                    cropped = self.roi_processor.crop(captured.image)
                    if cropped is not None and cropped.size > 0:
                        frame_to_process = cropped

                # 6. Jalankan inferensi backend aktif (YOLOv8 Neural Network atau HybridDetector)
                t0 = time.perf_counter()

                if self._detector_backend == "yolo" and self.yolo_detector.session is not None:
                    # Jalankan inferensi YOLOv8-Nano ONNX
                    yolo_res: YoloDetectionResult = self.yolo_detector.process_frame(
                        frame=frame_to_process,
                        frame_index=captured.frame_index,
                        timestamp=captured.timestamp,
                    )
                    t_elapsed = (time.perf_counter() - t0) * 1000.0
                    self._last_latency_ms = t_elapsed

                    best_target = yolo_res.best_target
                    is_leap = False
                    kinematic_state = "SEARCHING"
                    motion_elev_px = 0.0

                    if best_target is not None:
                        # Hitung koordinat bounding box relatif terhadap full viewport
                        rx, ry = 0, 0
                        if self.roi_processor is not None and self.roi_processor.config.enabled:
                            rx, ry = self.roi_processor.config.x, self.roi_processor.config.y
                        tb_x, tb_y, tb_w, tb_h = best_target.bbox
                        full_bbox = (tb_x + rx, tb_y + ry, tb_w, tb_h)

                        # Kinematika trajektori aksi Leap (Day 29)
                        action_res: ActionRecognitionResult = self.trajectory_action_detector.update(
                            bbox=best_target.bbox,
                            confidence=best_target.confidence,
                            timestamp=captured.timestamp,
                        )
                        is_leap = action_res.is_leap_detected
                        kinematic_state = action_res.state.value
                        motion_elev_px = action_res.elevation_px

                        # Fusi Multi-Class Neural Vision (Pose Leap Terdeteksi Langsung)
                        if best_target.class_name == "hidden_leap_airborne" and best_target.confidence >= 0.38:
                            is_leap = True
                            kinematic_state = "AIRBORNE_NEURAL"
                        elif best_target.class_name == "hidden_mark_stab":
                            kinematic_state = "MARK_STAB"
                        elif best_target.class_name == "hidden_grounded":
                            if not is_leap:
                                kinematic_state = "GROUNDED"

                        # Pancarkan target_tracked real-time ke UI untuk visualisasi bounding box
                        self.target_tracked.emit(
                            {
                                "bbox": full_bbox,
                                "confidence": best_target.confidence,
                                "template": best_target.class_name,
                                "is_detected": is_leap,
                                "strategy": f"YOLO_{kinematic_state}",
                            }
                        )

                        # Jika Leap terkonfirmasi valid via lonjakan vertikal, pancarkan AbilityEvent
                        if is_leap:
                            event = AbilityEvent(
                                killer_id="the_hidden",
                                ability_id="leap",
                                event_type="cast_start",
                                timestamp=captured.timestamp,
                                source="vision",
                                confidence=best_target.confidence,
                            )
                            logger.info(
                                "DetectionWorker: YOLO LEAP ACTION CONFIRMED -> %s [conf=%.2f, elev=%.1fpx, Vy=%.1fpx/s, lat=%.1fms]",
                                event.ability_id,
                                event.confidence,
                                action_res.elevation_px,
                                action_res.vertical_velocity_px_s,
                                t_elapsed,
                            )
                            self.ability_detected.emit(event)
                    else:
                        # Target hilang sejenak, perbarui tracker
                        self.trajectory_action_detector.update(
                            bbox=None,
                            confidence=0.0,
                            timestamp=captured.timestamp,
                        )

                    # Update telemetry
                    state_label = kinematic_state
                    conf_val = best_target.confidence if best_target else 0.0
                    tmpl_val = best_target.confidence if best_target else 0.0
                    strat_label = f"YOLO_SIMD_{self.trajectory_action_detector.state.value}"
                    is_det = is_leap
                else:
                    # Jalankan inferensi fallback HybridDetector
                    eval_res: HybridDetectionEvaluation = self.hybrid_detector.process_frame(
                        frame=frame_to_process,
                        frame_index=captured.frame_index,
                        timestamp=captured.timestamp,
                        audio_confirmed=self._audio_confirmed,
                    )
                    t_elapsed = (time.perf_counter() - t0) * 1000.0
                    self._last_latency_ms = t_elapsed

                    # Hitung koordinat target bounding box relatif terhadap full viewport
                    full_bbox = (0, 0, 0, 0)
                    if eval_res.target_bbox != (0, 0, 0, 0) and self.roi_processor is not None and self.roi_processor.config.enabled:
                        rx, ry = self.roi_processor.config.x, self.roi_processor.config.y
                        tb_x, tb_y, tb_w, tb_h = eval_res.target_bbox
                        full_bbox = (tb_x + rx, tb_y + ry, tb_w, tb_h)
                    else:
                        full_bbox = eval_res.target_bbox

                    # Pancarkan target_tracked real-time ke UI untuk visualisasi bounding box
                    if eval_res.template_score >= 0.35 or eval_res.is_detected:
                        self.target_tracked.emit(
                            {
                                "bbox": full_bbox,
                                "confidence": eval_res.template_score,
                                "template": eval_res.matched_template,
                                "is_detected": eval_res.is_detected,
                                "strategy": eval_res.fusion_strategy,
                            }
                        )

                    # Jika Leap terdeteksi valid, pancarkan AbilityEvent
                    if eval_res.is_detected and eval_res.detection_result is not None:
                        event: AbilityEvent = eval_res.detection_result.to_ability_event()
                        logger.info(
                            "DetectionWorker: EMITTING ABILITY EVENT -> %s/%s [conf=%.2f, strategy=%s, lat=%.1fms]",
                            event.killer_id,
                            event.ability_id,
                            event.confidence,
                            eval_res.fusion_strategy,
                            t_elapsed,
                        )
                        self.ability_detected.emit(event)

                    state_label = self.hybrid_detector.motion_detector.state
                    conf_val = eval_res.confidence
                    tmpl_val = eval_res.template_score
                    motion_elev_px = eval_res.motion_span_px
                    strat_label = eval_res.fusion_strategy
                    is_det = eval_res.is_detected

                # 7. Hitung telemetri performa worker
                self._frames_processed += 1
                now = time.monotonic()
                if (now - self._fps_start_time) >= 1.0:
                    self._current_fps = self._frames_processed / (now - self._fps_start_time)
                    self._frames_processed = 0
                    self._fps_start_time = now

                    # Pancarkan telemetri secara berkala ke UI thread
                    self.telemetry_updated.emit(
                        {
                            "state": state_label,
                            "is_detected": is_det,
                            "confidence": conf_val,
                            "template_score": tmpl_val,
                            "motion_span_px": motion_elev_px,
                            "latency_ms": round(self._last_latency_ms, 1),
                            "worker_fps": round(self._current_fps, 1),
                            "fusion_strategy": strat_label,
                        }
                    )

            except Exception as exc:
                logger.error("Exception in DetectionWorker loop: %s", exc, exc_info=True)
                self.worker_error.emit(str(exc))
                time.sleep(0.05)

        logger.info("DetectionWorker thread exited main loop.")
