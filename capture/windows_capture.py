"""
MSS Windows Screen Capture Engine
Violence District Cooldown Tracker
"""
import time
import threading
from collections import deque
from typing import Optional, Tuple
import cv2
import numpy as np
import mss

from capture.capture_interface import BaseCaptureEngine, CapturedFrame, CaptureStatus
from capture.frame_buffer import LatestFrameBuffer
from capture.window_helper import find_target_window, get_window_bounds
from app.logger import get_logger

logger = get_logger("capture")


class MSSWindowsCapture(BaseCaptureEngine):
    """
    Engine Capture berbasis Win32 GDI / BitBlt via pustaka MSS.
    Berjalan di Producer Thread independen dengan kontrol FPS dan alokasi frame terikat (bounded).
    """

    def __init__(self, buffer_size: int = 1):
        self._buffer = LatestFrameBuffer(maxsize=buffer_size)
        self._status = CaptureStatus.STOPPED
        self._target_title = "Roblox"
        self._target_fps = 30
        self._target_hwnd: Optional[int] = None

        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Metrik performa
        self._rolling_latencies = deque(maxlen=30)
        self._rolling_fps_timestamps = deque(maxlen=30)
        self._last_fps = 0.0
        self._last_latency = 0.0

    def start(self, target_title: str = "Roblox", target_fps: int = 30) -> bool:
        """Memulai capture loop pada thread terpisah."""
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                return True

            self._target_title = target_title
            self._target_fps = max(5, min(60, target_fps))
            self._stop_event.clear()
            self._status = CaptureStatus.STARTING

            logger.info("Starting capture worker thread for '%s' at target %d FPS", target_title, target_fps)
            self._worker_thread = threading.Thread(
                target=self._capture_worker,
                name="CaptureEngineThread",
                daemon=True
            )
            self._worker_thread.start()
            return True

    def stop(self) -> None:
        """Menghentikan thread capture dengan aman (clean shutdown)."""
        logger.info("Stopping capture engine...")
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None

        with self._lock:
            self._status = CaptureStatus.STOPPED
            self._buffer.clear()
        logger.info("Capture engine stopped and buffer cleared.")

    def get_latest_frame(self) -> Optional[CapturedFrame]:
        """Mengambil frame terbaru dari buffer (Consumer)."""
        return self._buffer.get_latest()

    @property
    def is_running(self) -> bool:
        return self._status in (CaptureStatus.RUNNING, CaptureStatus.STARTING)

    @property
    def status(self) -> CaptureStatus:
        with self._lock:
            return self._status

    @property
    def current_fps(self) -> float:
        with self._lock:
            return self._last_fps

    @property
    def current_latency_ms(self) -> float:
        with self._lock:
            return self._last_latency

    def _capture_worker(self) -> None:
        """Worker loop yang berjalan di background thread (Producer)."""
        target_frame_time = 1.0 / self._target_fps
        frame_index = 0

        with mss.MSS() as sct:
            while not self._stop_event.is_set():
                loop_start = time.perf_counter()

                # 1. Resolusi HWND & Koordinat Target
                bounds = None
                if self._target_hwnd:
                    bounds = get_window_bounds(self._target_hwnd)

                if bounds is None:
                    # Cari ulang window
                    win_info = find_target_window(self._target_title)
                    if win_info:
                        self._target_hwnd = win_info["hwnd"]
                        bounds = win_info["bounds"]
                        logger.info("Bound to target window '%s' (HWND: %s, Bounds: %s)", win_info["title"], win_info["hwnd"], bounds)
                    else:
                        with self._lock:
                            if self._status != CaptureStatus.TARGET_LOST:
                                logger.warning("Target window '%s' not found or minimized -> TARGET_LOST", self._target_title)
                            self._status = CaptureStatus.TARGET_LOST
                            self._target_hwnd = None
                            self._buffer.clear()
                        # Tunggu sebentar sebelum scan ulang agar tidak membebani CPU
                        time.sleep(0.3)
                        continue

                x, y, w, h = bounds
                monitor = {"top": y, "left": x, "width": w, "height": h}

                # 2. Capture Frame
                t0 = time.perf_counter()
                try:
                    raw = sct.grab(monitor)
                    raw_np = np.asarray(raw, dtype=np.uint8)  # BGRA
                    bgr_frame = cv2.cvtColor(raw_np, cv2.COLOR_BGRA2BGR)
                except Exception as exc:
                    logger.error("Capture grab failed: %s", exc)
                    with self._lock:
                        self._status = CaptureStatus.ERROR
                    time.sleep(0.1)
                    continue

                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000.0

                # 3. Masukkan ke Bounded Buffer
                frame_obj = CapturedFrame(
                    image=bgr_frame,
                    timestamp=time.monotonic(),
                    frame_index=frame_index,
                    width=w,
                    height=h,
                    latency_ms=latency_ms
                )
                self._buffer.push(frame_obj)
                frame_index += 1

                # 4. Kalkulasi Metrik (Rolling Average)
                with self._lock:
                    self._status = CaptureStatus.RUNNING
                    self._rolling_latencies.append(latency_ms)
                    self._rolling_fps_timestamps.append(loop_start)

                    if len(self._rolling_latencies) > 0:
                        self._last_latency = sum(self._rolling_latencies) / len(self._rolling_latencies)

                    if len(self._rolling_fps_timestamps) > 1:
                        time_span = self._rolling_fps_timestamps[-1] - self._rolling_fps_timestamps[0]
                        if time_span > 0:
                            self._last_fps = (len(self._rolling_fps_timestamps) - 1) / time_span

                # 5. Rate Limiter (Menjaga target FPS)
                elapsed = time.perf_counter() - loop_start
                sleep_duration = target_frame_time - elapsed
                if sleep_duration > 0.001:
                    time.sleep(sleep_duration)

        with self._lock:
            self._status = CaptureStatus.STOPPED
