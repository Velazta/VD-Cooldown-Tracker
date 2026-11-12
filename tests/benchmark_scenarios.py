"""
Automated Benchmark Runner (5 Scenarios)
Violence District Cooldown Tracker — Day 5 (Segmen 5.3)
Sesuai PRD Bab 4.1 & Bab 9.2:
1. Idle (Baseline aplikasi tanpa capture)
2. Full-frame Raw Capture (1080p)
3. ROI Cropped Capture (Play-Area 1280x780)
4. ROI + CLAHE Preprocessing (Night Enhancement)
5. Sustained Stability Test (Continuous run)
"""
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

# Pastikan root direktori proyek ada di sys.path agar modul capture/processing/monitoring terbaca
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from capture.windows_capture import MSSWindowsCapture
from processing.roi_processor import ROIConfig, ROIProcessor
from processing.preprocessing import ImagePreprocessor, PreprocessingConfig, PreprocessorMode
from monitoring.performance_monitor import PerformanceMonitor


def run_scenario_idle(duration_sec: float = 3.0) -> Dict[str, Any]:
    """Skenario 1: Idle (Aplikasi berjalan tanpa capture engine)."""
    print("\n[RUNNING] Skenario 1: Idle (Aplikasi standby tanpa capture)...")
    monitor = PerformanceMonitor(history_size=30, target_process_name="Roblox")

    t_end = time.monotonic() + duration_sec
    while time.monotonic() < t_end:
        monitor.sample_metrics()
        time.sleep(0.2)

    summary = monitor.get_summary()
    return {
        "scenario": "1. Idle (No Capture)",
        "duration_sec": duration_sec,
        "capture_fps": 0.0,
        "processing_fps": 0.0,
        "capture_lat_ms": 0.0,
        "cv_proc_lat_ms": 0.0,
        "app_cpu_avg": summary.get("cpu_avg", 0.0),
        "app_cpu_max": summary.get("cpu_max", 0.0),
        "app_ram_avg_mb": summary.get("ram_avg_mb", 0.0),
        "app_ram_max_mb": summary.get("ram_max_mb", 0.0),
    }


def run_scenario_full_capture(engine: MSSWindowsCapture, duration_sec: float = 5.0) -> Dict[str, Any]:
    """Skenario 2: Full-frame Raw Capture (1080p tanpa ROI)."""
    print("\n[RUNNING] Skenario 2: Full-frame Raw Capture (1080p)...")
    monitor = PerformanceMonitor(history_size=60, target_process_name="Roblox")

    engine.start(target_title="Roblox", target_fps=30)
    time.sleep(0.5)  # Warm-up

    t_end = time.monotonic() + duration_sec
    while time.monotonic() < t_end:
        t0 = time.perf_counter()
        frame_data = engine.get_latest_frame()
        if frame_data is not None:
            monitor.record_capture_frame(frame_data.latency_ms)
        monitor.sample_metrics()
        time.sleep(0.033)

    engine.stop()
    summary = monitor.get_summary()
    return {
        "scenario": "2. Full 1080p Raw Capture",
        "duration_sec": duration_sec,
        "capture_fps": summary.get("capture_fps_avg", 0.0),
        "processing_fps": 0.0,
        "capture_lat_ms": summary.get("capture_lat_avg_ms", 0.0),
        "cv_proc_lat_ms": 0.0,
        "app_cpu_avg": summary.get("cpu_avg", 0.0),
        "app_cpu_max": summary.get("cpu_max", 0.0),
        "app_ram_avg_mb": summary.get("ram_avg_mb", 0.0),
        "app_ram_max_mb": summary.get("ram_max_mb", 0.0),
    }


def run_scenario_roi_capture(engine: MSSWindowsCapture, duration_sec: float = 5.0) -> Dict[str, Any]:
    """Skenario 3: Capture aktif dengan ROI Play-Area (1280x780)."""
    print("\n[RUNNING] Skenario 3: Capture + ROI Cropping (1280x780)...")
    monitor = PerformanceMonitor(history_size=60, target_process_name="Roblox")
    roi_proc = ROIProcessor(ROIConfig(x=320, y=150, width=1280, height=780, enabled=True))

    engine.start(target_title="Roblox", target_fps=30)
    time.sleep(0.5)

    roi_crop_latencies = []
    t_end = time.monotonic() + duration_sec
    while time.monotonic() < t_end:
        frame_data = engine.get_latest_frame()
        if frame_data is not None:
            monitor.record_capture_frame(frame_data.latency_ms)

            # Crop ROI
            t_crop0 = time.perf_counter()
            cropped = roi_proc.crop(frame_data.image)
            t_crop1 = time.perf_counter()

            if cropped is not None:
                crop_ms = (t_crop1 - t_crop0) * 1000.0
                roi_crop_latencies.append(crop_ms)
                monitor.record_processing_frame(crop_ms)

        monitor.sample_metrics()
        time.sleep(0.033)

    engine.stop()
    summary = monitor.get_summary()
    avg_crop_ms = sum(roi_crop_latencies) / len(roi_crop_latencies) if roi_crop_latencies else 0.0
    return {
        "scenario": "3. ROI Cropping (1280x780)",
        "duration_sec": duration_sec,
        "capture_fps": summary.get("capture_fps_avg", 0.0),
        "processing_fps": summary.get("processing_fps_avg", 0.0),
        "capture_lat_ms": summary.get("capture_lat_avg_ms", 0.0),
        "cv_proc_lat_ms": round(avg_crop_ms, 2),
        "app_cpu_avg": summary.get("cpu_avg", 0.0),
        "app_cpu_max": summary.get("cpu_max", 0.0),
        "app_ram_avg_mb": summary.get("ram_avg_mb", 0.0),
        "app_ram_max_mb": summary.get("ram_max_mb", 0.0),
    }


def run_scenario_roi_clahe(engine: MSSWindowsCapture, duration_sec: float = 5.0) -> Dict[str, Any]:
    """Skenario 4: Capture + ROI + Preprocessing CLAHE."""
    print("\n[RUNNING] Skenario 4: Capture + ROI + CLAHE Preprocessing...")
    monitor = PerformanceMonitor(history_size=60, target_process_name="Roblox")
    roi_proc = ROIProcessor(ROIConfig(x=320, y=150, width=1280, height=780, enabled=True))
    preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.CLAHE))

    engine.start(target_title="Roblox", target_fps=30)
    time.sleep(0.5)

    cv_latencies = []
    t_end = time.monotonic() + duration_sec
    while time.monotonic() < t_end:
        frame_data = engine.get_latest_frame()
        if frame_data is not None:
            monitor.record_capture_frame(frame_data.latency_ms)

            cropped = roi_proc.crop(frame_data.image)
            if cropped is not None:
                processed, cv_ms = preprocessor.process(cropped)
                cv_latencies.append(cv_ms)
                monitor.record_processing_frame(cv_ms)

        monitor.sample_metrics()
        time.sleep(0.033)

    engine.stop()
    summary = monitor.get_summary()
    avg_cv_ms = sum(cv_latencies) / len(cv_latencies) if cv_latencies else 0.0
    return {
        "scenario": "4. ROI + CLAHE Preprocessing",
        "duration_sec": duration_sec,
        "capture_fps": summary.get("capture_fps_avg", 0.0),
        "processing_fps": summary.get("processing_fps_avg", 0.0),
        "capture_lat_ms": summary.get("capture_lat_avg_ms", 0.0),
        "cv_proc_lat_ms": round(avg_cv_ms, 2),
        "app_cpu_avg": summary.get("cpu_avg", 0.0),
        "app_cpu_max": summary.get("cpu_max", 0.0),
        "app_ram_avg_mb": summary.get("ram_avg_mb", 0.0),
        "app_ram_max_mb": summary.get("ram_max_mb", 0.0),
    }


def run_scenario_sustained_stability(engine: MSSWindowsCapture, duration_sec: float = 10.0) -> Dict[str, Any]:
    """Skenario 5: Sustained Stability Test (Pengujian Kestabilan Berkelanjutan 10 detik)."""
    print(f"\n[RUNNING] Skenario 5: Sustained Stability Test ({duration_sec}s continuous)...")
    monitor = PerformanceMonitor(history_size=120, target_process_name="Roblox")
    roi_proc = ROIProcessor(ROIConfig(x=320, y=150, width=1280, height=780, enabled=True))
    preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.CLAHE))

    engine.start(target_title="Roblox", target_fps=30)
    time.sleep(0.5)

    cv_latencies = []
    t_end = time.monotonic() + duration_sec
    while time.monotonic() < t_end:
        frame_data = engine.get_latest_frame()
        if frame_data is not None:
            monitor.record_capture_frame(frame_data.latency_ms)

            cropped = roi_proc.crop(frame_data.image)
            if cropped is not None:
                _, cv_ms = preprocessor.process(cropped)
                cv_latencies.append(cv_ms)
                monitor.record_processing_frame(cv_ms)

        monitor.sample_metrics()
        time.sleep(0.033)

    engine.stop()
    summary = monitor.get_summary()
    avg_cv_ms = sum(cv_latencies) / len(cv_latencies) if cv_latencies else 0.0
    return {
        "scenario": f"5. Sustained Run ({duration_sec}s)",
        "duration_sec": duration_sec,
        "capture_fps": summary.get("capture_fps_avg", 0.0),
        "processing_fps": summary.get("processing_fps_avg", 0.0),
        "capture_lat_ms": summary.get("capture_lat_avg_ms", 0.0),
        "cv_proc_lat_ms": round(avg_cv_ms, 2),
        "app_cpu_avg": summary.get("cpu_avg", 0.0),
        "app_cpu_max": summary.get("cpu_max", 0.0),
        "app_ram_avg_mb": summary.get("ram_avg_mb", 0.0),
        "app_ram_max_mb": summary.get("ram_max_mb", 0.0),
    }


def main():
    print("=" * 80)
    print("  AUTOMATED BENCHMARK SUITE — VIOLENCE DISTRICT TRACKER (DAY 5)")
    print("=" * 80)

    engine = MSSWindowsCapture(buffer_size=1)
    results: List[Dict[str, Any]] = []

    # Eksekusi 5 Skenario
    results.append(run_scenario_idle(duration_sec=3.0))
    results.append(run_scenario_full_capture(engine, duration_sec=5.0))
    results.append(run_scenario_roi_capture(engine, duration_sec=5.0))
    results.append(run_scenario_roi_clahe(engine, duration_sec=5.0))
    results.append(run_scenario_sustained_stability(engine, duration_sec=10.0))

    # Tampilkan Tabel Hasil
    print("\n" + "=" * 96)
    print(f"{'Skenario':<30} | {'Cap FPS':>7} | {'Proc FPS':>8} | {'Cap Lat':>8} | {'CV Lat':>7} | {'CPU Avg':>7} | {'RAM Avg':>9}")
    print("-" * 96)

    for r in results:
        name = r["scenario"]
        c_fps = f"{r['capture_fps']:.1f}"
        p_fps = f"{r['processing_fps']:.1f}"
        c_lat = f"{r['capture_lat_ms']:.1f}ms"
        v_lat = f"{r['cv_proc_lat_ms']:.1f}ms"
        cpu = f"{r['app_cpu_avg']:.1f}%"
        ram = f"{r['app_ram_avg_mb']:.1f}MB"
        print(f"{name:<30} | {c_fps:>7} | {p_fps:>8} | {c_lat:>8} | {v_lat:>7} | {cpu:>7} | {ram:>9}")

    print("=" * 96)

    # Simpan Hasil ke JSON untuk Dokumentasi Deliverable Segmen 5.4
    output_path = Path("dataset/benchmark_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"\n[OK] Seluruh data benchmark berhasil diexport ke: {output_path}")


if __name__ == "__main__":
    main()
