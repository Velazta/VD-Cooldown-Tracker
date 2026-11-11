"""
Technical Spike: Capture Benchmark
Menguji performa capture backend, mengukur latensi, dan menyimpan bukti frame.
"""
import time
import os
from pathlib import Path
import cv2
import numpy as np

# Import helper pencari window
from spike_window_helper import find_target_windows

def benchmark_mss_backend(target_bounds=None, iterations=60):
    """Pengujian Baseline: Win32 GDI via MSS"""
    try:
        import mss
    except ImportError:
        print("[-] Library 'mss' belum terinstall.")
        return None

    print("\n--- Menguji Backend: MSS (GDI BitBlt) ---")
    with mss.mss() as sct:
        if target_bounds:
            x, y, w, h = target_bounds
            monitor = {"top": y, "left": x, "width": w, "height": h}
        else:
            monitor = sct.monitors[1]  # Primary monitor

        # Warm-up 5 frames
        for _ in range(5):
            _ = sct.grab(monitor)

        latencies = []
        last_frame = None

        start_total = time.perf_counter()
        for _ in range(iterations):
            t0 = time.perf_counter()
            raw = sct.grab(monitor)
            frame = np.array(raw, dtype=np.uint8)  # BGRA
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000)
            last_frame = frame_bgr
        
        total_time = time.perf_counter() - start_total

        avg_latency = np.mean(latencies)
        max_fps = iterations / total_time
        print(f"[RESULT MSS] Avg Latency: {avg_latency:.2f} ms | Max FPS: {max_fps:.1f} FPS | Resolution: {last_frame.shape[1]}x{last_frame.shape[0]}")
        return avg_latency, max_fps, last_frame

def benchmark_bettercam_backend(target_bounds=None, iterations=60):
    """Pengujian Alternatif: DXGI Desktop Duplication via BetterCam / DXCam"""
    try:
        import bettercam
    except ImportError:
        try:
            import dxcam as bettercam
        except ImportError:
            print("[-] Library 'bettercam/dxcam' belum terinstall.")
            return None

    print("\n--- Menguji Backend: BetterCam (DXGI Desktop Duplication) ---")
    camera = bettercam.create(output_idx=0, output_color="BGR")
    
    region = None
    if target_bounds:
        x, y, w, h = target_bounds
        region = (x, y, x + w, y + h)

    # Warm-up
    for _ in range(5):
        _ = camera.grab(region=region)

    latencies = []
    last_frame = None

    start_total = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        frame = camera.grab(region=region)
        t1 = time.perf_counter()
        if frame is not None:
            latencies.append((t1 - t0) * 1000)
            last_frame = frame

    del camera
    total_time = time.perf_counter() - start_total

    if latencies and last_frame is not None:
        avg_latency = np.mean(latencies)
        max_fps = len(latencies) / total_time
        print(f"[RESULT DXGI] Avg Latency: {avg_latency:.2f} ms | Max FPS: {max_fps:.1f} FPS | Resolution: {last_frame.shape[1]}x{last_frame.shape[0]}")
        return avg_latency, max_fps, last_frame
    else:
        print("[!] DXGI Grab mengembalikan None (jendela mungkin diminimalkan atau tidak ada perubahan visual).")
        return None

def benchmark_windows_capture_backend(hwnd, iterations=60):
    """Pengujian Pilihan Utama PRD: Windows.Graphics.Capture (WGC)"""
    try:
        from windows_capture import WindowsCapture, Frame, InternalCaptureControl
    except ImportError:
        print("[-] Library 'windows-capture' belum terinstall.")
        return None

    print("\n--- Menguji Backend: Windows.Graphics.Capture (WGC) ---")
    captured_frames = []
    latencies = []
    last_time = [time.perf_counter()]

    def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
        t_now = time.perf_counter()
        latencies.append((t_now - last_time[0]) * 1000)
        last_time[0] = t_now
        
        # Konversi ke NumPy BGR
        np_frame = frame.convert_to_bgr().frame_buffer
        captured_frames.append(np_frame)

        if len(captured_frames) >= iterations:
            capture_control.stop()

    def on_closed():
        pass

    capture = WindowsCapture(
        cursor_capture=False,
        draw_border=False,
        monitor_index=None,
        window_name=None,
    )
    # Target via hwnd atau window name
    # Diuji via session
    print("[*] WGC Session diinisialisasi...")
    return None  # Handler detail dipanggil saat spike WGC interaktif

def main():
    print("=" * 60)
    print("  DAY 2: TECHNICAL SPIKE - SCREEN CAPTURE BENCHMARK")
    print("=" * 60)

    # 1. Cari target
    targets = find_target_windows("Roblox")
    target_bounds = None
    if targets:
        target = targets[0]
        print(f"[TARGET] Menemukan Roblox: '{target['title']}' di {target['bounds']}")
        target_bounds = target['bounds']
    else:
        print("[INFO] Roblox tidak terdeteksi aktif. Spike akan menguji Primary Monitor / Desktop.")

    # 2. Pastikan folder output ada
    output_dir = Path("dataset")
    output_dir.mkdir(exist_ok=True)

    # 3. Jalankan Benchmark
    results = {}

    # Test BetterCam (DXGI)
    res_dxgi = benchmark_bettercam_backend(target_bounds)
    if res_dxgi:
        results["DXGI"] = res_dxgi

    # Test MSS (GDI)
    res_mss = benchmark_mss_backend(target_bounds)
    if res_mss:
        results["MSS"] = res_mss

    # 4. Simpan Bukti Frame (Deliverable Day 2)
    saved_sample = None
    for name, (_, _, frame) in results.items():
        if frame is not None:
            sample_path = output_dir / "spike_test_frame.png"
            cv2.imwrite(str(sample_path), frame)
            saved_sample = sample_path
            print(f"\n[OK] Berhasil menyimpan sample frame dari {name} ke: {sample_path}")
            break

    # 5. Evaluasi Kriteria Lulus Day 2
    print("\n" + "=" * 60)
    print("  HASIL EVALUASI TECHNICAL SPIKE")
    print("=" * 60)
    for name, (lat, fps, frame) in results.items():
        status = "MEMENUHI TARGET (<150ms & >30 FPS)" if lat < 33.0 and fps >= 30 else "BELUM OPTIMAL"
        print(f"Backend {name:8} : {lat:6.2f} ms/frame | Kapasitas: {fps:5.1f} FPS -> {status}")

    if saved_sample and saved_sample.exists():
        print(f"\n[ACCEPTANCE CRITERIA DAY 2] LULUS: Frame berhasil diperoleh dan disimpan.")
    else:
        print(f"\n[!] Belum ada frame yang tersimpan. Pastikan minimal satu backend capture terinstall.")

if __name__ == "__main__":
    main()