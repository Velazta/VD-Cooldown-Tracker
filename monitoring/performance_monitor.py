"""
Performance Monitor & Telemetry Module
Violence District Cooldown Tracker
"""
import time
import os
import threading
from dataclasses import dataclass
from collections import deque
from typing import Optional, Dict, Any, List

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


@dataclass
class PerformanceSnapshot:
    """Snapshot metrik sistem pada titik waktu tertentu."""
    timestamp: float
    app_cpu_percent: float
    app_ram_rss_mb: float
    capture_fps: float
    processing_fps: float
    capture_latency_ms: float
    processing_latency_ms: float
    target_cpu_percent: Optional[float] = None
    target_ram_rss_mb: Optional[float] = None


class PerformanceMonitor:
    """
    Monitor kinerja non-blocking untuk memantau resource aplikasi dan game.
    Menggunakan rolling buffers untuk FPS & latensi serta psutil untuk CPU/RAM.
    """

    def __init__(self, history_size: int = 60, target_process_name: str = "Roblox"):
        self._history_size = max(10, history_size)
        self._target_process_name = target_process_name
        self._lock = threading.Lock()

        # Objek proses aplikasi saat ini
        self._app_process = psutil.Process(os.getpid()) if HAS_PSUTIL else None
        if self._app_process:
            # Panggilan pertama cpu_percent untuk menginisialisasi titik referensi
            self._app_process.cpu_percent(interval=None)

        # Cache objek proses Roblox
        self._target_process: Optional[Any] = None
        self._last_target_scan_time = 0.0

        # Rolling buffers untuk latensi dan timestamps (thread-safe)
        self._capture_timestamps = deque(maxlen=30)
        self._capture_latencies = deque(maxlen=30)
        self._processing_timestamps = deque(maxlen=30)
        self._processing_latencies = deque(maxlen=30)

        # Snapshot history untuk analisis ringkasan
        self._snapshot_history = deque(maxlen=self._history_size)

    def record_capture_frame(self, latency_ms: float) -> None:
        """Mencatat kedatangan satu frame dari capture engine."""
        now = time.monotonic()
        with self._lock:
            self._capture_timestamps.append(now)
            self._capture_latencies.append(latency_ms)

    def record_processing_frame(self, latency_ms: float) -> None:
        """Mencatat penyelesaian satu frame dari pipeline processing."""
        now = time.monotonic()
        with self._lock:
            self._processing_timestamps.append(now)
            self._processing_latencies.append(latency_ms)

    def _get_target_process(self) -> Optional[Any]:
        """Menemukan proses target (Roblox) dengan caching agar tidak membebani CPU."""
        if not HAS_PSUTIL:
            return None

        now = time.monotonic()
        if self._target_process is not None:
            try:
                if self._target_process.is_running():
                    return self._target_process
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._target_process = None

        # Re-scan hanya tiap 3 detik
        if now - self._last_target_scan_time > 3.0:
            self._last_target_scan_time = now
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pname = proc.info.get("name") or ""
                    if self._target_process_name.lower() in pname.lower():
                        self._target_process = proc
                        # Inisialisasi cpu_percent
                        self._target_process.cpu_percent(interval=None)
                        return self._target_process
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        return self._target_process

    def sample_metrics(self) -> PerformanceSnapshot:
        """
        Mengambil snapshot metrik terkini secara non-blocking (interval=None).
        """
        now = time.monotonic()

        # 1. Metrik Aplikasi (CPU & RAM RSS)
        app_cpu = 0.0
        app_ram = 0.0
        if self._app_process:
            try:
                app_cpu = self._app_process.cpu_percent(interval=None)
                app_ram = self._app_process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        # 2. Metrik Target Roblox (jika aktif)
        target_cpu = None
        target_ram = None
        target_proc = self._get_target_process()
        if target_proc:
            try:
                target_cpu = target_proc.cpu_percent(interval=None)
                target_ram = target_proc.memory_info().rss / (1024 * 1024)
            except Exception:
                self._target_process = None

        # 3. Hitung Rolling FPS & Latensi
        with self._lock:
            # Capture FPS
            cap_fps = 0.0
            if len(self._capture_timestamps) > 1:
                dt = self._capture_timestamps[-1] - self._capture_timestamps[0]
                if dt > 0:
                    cap_fps = (len(self._capture_timestamps) - 1) / dt
            cap_lat = sum(self._capture_latencies) / len(self._capture_latencies) if self._capture_latencies else 0.0

            # Processing FPS
            proc_fps = 0.0
            if len(self._processing_timestamps) > 1:
                dt = self._processing_timestamps[-1] - self._processing_timestamps[0]
                if dt > 0:
                    proc_fps = (len(self._processing_timestamps) - 1) / dt
            proc_lat = sum(self._processing_latencies) / len(self._processing_latencies) if self._processing_latencies else 0.0

            snapshot = PerformanceSnapshot(
                timestamp=now,
                app_cpu_percent=round(app_cpu, 2),
                app_ram_rss_mb=round(app_ram, 2),
                capture_fps=round(cap_fps, 1),
                processing_fps=round(proc_fps, 1),
                capture_latency_ms=round(cap_lat, 2),
                processing_latency_ms=round(proc_lat, 2),
                target_cpu_percent=round(target_cpu, 2) if target_cpu is not None else None,
                target_ram_rss_mb=round(target_ram, 2) if target_ram is not None else None
            )
            self._snapshot_history.append(snapshot)
            return snapshot

    def get_summary(self) -> Dict[str, Any]:
        """Menghitung ringkasan statistik (mean, min, max) dari snapshot history."""
        with self._lock:
            if not self._snapshot_history:
                return {}

            cpus = [s.app_cpu_percent for s in self._snapshot_history]
            rams = [s.app_ram_rss_mb for s in self._snapshot_history]
            cap_fps_list = [s.capture_fps for s in self._snapshot_history]
            proc_fps_list = [s.processing_fps for s in self._snapshot_history]
            cap_lats = [s.capture_latency_ms for s in self._snapshot_history if s.capture_latency_ms > 0]
            proc_lats = [s.processing_latency_ms for s in self._snapshot_history if s.processing_latency_ms > 0]

            return {
                "sample_count": len(self._snapshot_history),
                "cpu_avg": round(sum(cpus) / len(cpus), 2),
                "cpu_max": round(max(cpus), 2),
                "ram_avg_mb": round(sum(rams) / len(rams), 2),
                "ram_max_mb": round(max(rams), 2),
                "capture_fps_avg": round(sum(cap_fps_list) / len(cap_fps_list), 1),
                "processing_fps_avg": round(sum(proc_fps_list) / len(proc_fps_list), 1),
                "capture_lat_avg_ms": round(sum(cap_lats) / len(cap_lats), 2) if cap_lats else 0.0,
                "processing_lat_avg_ms": round(sum(proc_lats) / len(proc_lats), 2) if proc_lats else 0.0,
            }
