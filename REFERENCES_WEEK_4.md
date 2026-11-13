# Week 4 — Development References & Implementation Guide (Day 19–24)

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 4 — End-to-End Integration, Live Pipeline & System Evaluation  
**Schedule:** 27 November – 3 Desember 2026  
**Target branch:** `dev`  
**Primary stack:** Python 3.14 (64-bit), PySide6 6.12, OpenCV 5.0, NumPy 2.5  
**Purpose:** Technical reference architecture, API guidelines, and day-by-day implementation blueprints aligned with `PRD_WEEK_4.md`.

---

## 1. Architectural Principles & Thread Concurrency Model

### 1.1 The Golden Rule of Desktop CV Applications: Never Block the UI Thread
Dalam aplikasi desktop yang menampilkan antarmuka real-time (PySide6) dan overlay melayang di atas game, pemrosesan citra komputer (OpenCV) dan inferensi audio tidak boleh dijalankan langsung di dalam main GUI thread (*event loop* Qt).
- Jika UI thread terblokir selama 60 ms oleh detektor, jendela overlay akan mengalami stutter, dan antarmuka akan menjadi *Not Responding*.
- **Solusi Arsitektural:** `DetectionWorker` dijalankan pada thread terpisah (`QThread` atau Python `threading.Thread`).

```text
+-----------------------------------------------------------------------------------+
|                                  MAIN PROCESS                                     |
|                                                                                   |
|  +-----------------------+                    +--------------------------------+  |
|  |   MSSWindowsCapture   |                    |       PySide6 GUI Thread       |  |
|  |   (Producer Thread)   |                    |                                |  |
|  +-----------+-----------+                    |   - CapturePreviewWindow       |  |
|              |                                |   - OverlayController (30 FPS) |  |
|              | latest CaptureFrame            |   - OverlayWindow (Click-thru) |  |
|              v                                +---------------+----------------+  |
|  +-----------------------+                                    ^                   |
|  | FrameRingBuffer       |                                    | Qt Signal         |
|  | (maxlen=1, drop-old)  |                                    | (AbilityEvent)    |
|  +-----------+-----------+                                    |                   |
|              |                                                |                   |
|              v latest frame                                   |                   |
|  +------------------------------------------------------------+----------------+  |
|  |                        DetectionWorker Thread                               |  |
|  |                                                                             |  |
|  |   1. Clamped Crop via ROIProcessor                                          |  |
|  |   2. Multi-Scale Template Match (TemplateDetector)                          |  |
|  |   3. Parabolic Centroid Tracking (MotionDetector)                           |  |
|  |   4. Audio FFT Bandpass Filter (AudioInspector)                             |  |
|  |   5. Fusion Decision (HybridDetector)                                       |  |
|  |   6. DetectionResult.to_ability_event() -> Emit to CooldownManager          |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Technical Standards & API References

### 2.1 Thread-Safe Inter-Thread Communication in PySide6
- **Qt Signals and Slots:** Gunakan sinyal Qt bertipe kuat (`Signal(object)`) untuk mengirimkan data hasil deteksi dari worker thread ke UI thread. Qt secara otomatis menangani mekanisme *QueuedConnection* yang aman melintasi batas thread.
- **Python Reference:** [PySide6 QThread Documentation](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
- **Pattern Terbaik:**
  ```python
  class DetectionWorker(QThread):
      ability_detected = Signal(object)  # Emits AbilityEvent
      telemetry_updated = Signal(dict)   # Emits metrics (fps, latency_ms)

      def __init__(self, capture_engine, hybrid_detector, roi_processor):
          super().__init__()
          self._running = True

      def run(self):
          while self._running:
              frame = self.capture_engine.get_latest_frame()
              if frame is not None:
                  result = self.hybrid_detector.process_frame(...)
                  if result.is_detected:
                      self.ability_detected.emit(result.detection_result.to_ability_event())
  ```

### 2.2 Windows Audio Loopback Capture
- **Tujuan:** Menangkap audio yang sedang diputar oleh game Roblox secara non-invasif tanpa memerlukan mikrofon fisik.
- **Standar API:** Windows Audio Session API (WASAPI) Loopback.
- **Pustaka Python:** Standard system audio capture via `soundcard` / `pyaudio` WASAPI loopback atau pembacaan buffer audio streaming.
- **Reference:** [Microsoft WASAPI Loopback Capture Documentation](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)

### 2.3 High-Precision Monotonic Timing & Profiling
- **`time.perf_counter()`:** Digunakan untuk mengukur waktu eksekusi interval pendek dengan resolusi sub-mikrodetik.
- **`time.monotonic()`:** Digunakan untuk timestamp absolut event cooldown dan masa kedaluwarsa debounce (kebal terhadap sinkronisasi jam Windows NTP).
- **Reference:** [Python time documentation](https://docs.python.org/3/library/time.html)

### 2.4 Non-Blocking Resource Profiling via `psutil`
- **CPU Tracking:** Panggil `process.cpu_percent(interval=None)` secara non-blocking di dalam timer periodik (misal: 1 detik sekali), bukan di dalam loop frame rendering.
- **Memory Tracking:** Gunakan `process.memory_info().rss / (1024 * 1024)` untuk membaca konsumsi memori fisik riil dalam megabyte.
- **Reference:** [psutil documentation](https://psutil.readthedocs.io/en/latest/)

---

## 3. Panduan Implementasi Harian (Day-by-Day Guide)

### Day 19 — Background Detection Worker & Real-Time Pipeline Wiring
**Tujuan:** Membangun `DetectionWorker` dan menyambungkan aliran frame capture ke `HybridDetector` dan `CooldownManager` di `main.py`.

#### Referensi Penting:
- `detection/hybrid_detector.py` — method `process_frame()` dan `process_frame_with_cached_match()`.
- `detection/detection_result.py` — method `.to_ability_event()`.
- `cooldown/cooldown_manager.py` — method `handle_event()`.
- `main.py` — inisialisasi thread dan sinyal koneksi.

#### Langkah Pelaksanaan:
1. Buat modul `detection/detection_worker.py` yang mewarisi `QThread`.
2. Sambungkan sinyal `ability_detected` dari `DetectionWorker` ke `self.cooldown_manager.handle_event()`.
3. Tambahkan komponen kontrol di GUI `main.py`:
   - Checkbox `[x] Aktifkan Deteksi Otomatis (Vision)`.
   - Readout status deteksi: Status (*IDLE / TRACKING / DETECTED*), Latensi inferensi (ms), dan FPS worker.
4. Uji emisi event: Saat frame synthetic atau video dimasukkan, pastikan cincin overlay melayang langsung merespons seketika.

**Deliverable:** `detection/detection_worker.py`, integrasi `main.py`, dan unit test `tests/test_detection_worker.py`.

---

### Day 20 — Temporal Debounce, Confidence Filtering & Audio Loopback
**Tujuan:** Menyempurnakan filter deteksi agar kebal terhadap noise dan mengintegrasikan audio spectral gating real-time.

#### Referensi Penting:
- `dataset/DAY18_ERROR_ANALYSIS.md` — bukti eliminasi 191 false positive melalui audio gating.
- `tools/audio_inspector.py` — kalkulasi rasio energi bandpass FFT (100–3.500 Hz vs > 3.500 Hz).

#### Langkah Pelaksanaan:
1. Hubungkan slider sensitivitas di GUI ke atribut `confidence_threshold` pada `TemplateDetector`.
2. Implementasikan modul audio loopback non-blocking (`detection/audio_capture.py`) untuk menyuplai status `audio_confirmed`.
3. Uji fallback: Pastikan jika audio dimatikan, proteksi debounce temporal (1.5s) dan kinematika lonjakan vertikal tetap menjaga sistem dari false alarms.
4. Verifikasi fallback manual: Pastikan penekanan hotkey `F1`–`F4` tetap berfungsi mulus berdampingan dengan detektor otomatis.

**Deliverable:** `detection/audio_capture.py`, unit test `tests/test_live_pipeline.py`.

---

### Day 21 — Live Latency Measurement & Cooldown Calibration
**Tujuan:** Mengukur latensi end-to-end secara akurat dan mengalibrasi durasi cooldown Leap di game.

#### Referensi Penting:
- `PRD.md` Bab 8 — batas target latensi (< 150 ms acceptance, < 100 ms stretch goal).
- `tools/evaluate_baseline.py` — kalkulasi mean dan P95 percentile latensi.

#### Langkah Pelaksanaan:
1. Buat skrip pengukur latensi `tools/latency_benchmarker.py`:
   - Mengukur $T_{\text{capture}} \rightarrow T_{\text{inferensi}} \rightarrow T_{\text{dispatch}} \rightarrow T_{\text{overlay\_repaint}}$.
2. Catat distribusi latensi (rata-rata, median, P95, P99).
3. Kalibrasi durasi cooldown The Hidden Leap pada `killerDatabase.json` berdasarkan pengukuran aktual gameplay.
4. Hasilkan laporan [dataset/LATENCY_BENCHMARK.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/LATENCY_BENCHMARK.md).

**Deliverable:** `tools/latency_benchmarker.py` dan `dataset/LATENCY_BENCHMARK.md`.

---

### Day 22 — Hardware Resource Profiling & Game FPS Impact
**Tujuan:** Membuktikan bahwa aplikasi sangat ringan dan tidak menyebabkan drop FPS di Roblox.

#### Referensi Penting:
- `monitoring/performance_monitor.py` — model data telemetri performa sistem.

#### Langkah Pelaksanaan:
1. Jalankan aplikasi secara berdampingan dengan Roblox Violence District.
2. Ukur FPS game Roblox saat overlay aktif vs saat aplikasi ditutup.
3. Ukur penggunaan CPU total sistem dan CPU khusus proses Python (target < 5.0%).
4. Ukur konsumsi memori fisik RAM aplikasi (target < 250 MB).
5. Susun laporan formal [dataset/HARDWARE_AUDIT.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/HARDWARE_AUDIT.md).

**Deliverable:** Laporan audit hardware empiris.

---

### Day 23 — 1-Hour Long-Run Continuous Stability Stress Test
**Tujuan:** Menjamin keandalan jangka panjang tanpa crash atau kebocoran memori.

#### Referensi Penting:
- `tests/test_stability.py` — pengujian lifecycle restart dan clean shutdown.

#### Langkah Pelaksanaan:
1. Buat harness pengujian kontinu `tools/stability_runner.py` untuk menjalankan streaming frame selama 1 jam (3.600 detik / ~72.000 frame).
2. Uji penanganan kondisi anomali:
   - Jendela Roblox di-minimize dan di-restore.
   - Resolusi layar diubah.
   - Game Roblox ditutup dan dibuka kembali saat aplikasi sedang berjalan.
3. Pastikan memori RAM tetap datar (*flat memory curve*) tanpa gejala kebocoran memori.

**Deliverable:** `tools/stability_runner.py`, log kestabilan 1 jam, dan test `tests/test_longrun_stability.py`.

---

### Day 24 — Final Integration QA, Week 4 Milestone Report & Release Tag
**Tujuan:** Menuntaskan evaluasi Week 4 dan mengunci rilis milestone integrasi penuh.

#### Langkah Pelaksanaan:
1. Jalankan seluruh test suite dari Week 1 sampai Week 4 (target > 135 tests passing).
2. Periksa kesesuaian seluruh Acceptance Criteria pada `PRD_WEEK_4.md`.
3. Susun dokumen penutup [dataset/WEEK4_FINAL_REPORT.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/WEEK4_FINAL_REPORT.md).
4. Perbarui `TODO.md` dan `ARCHITECTURE.md`.
5. Beri tag rilis Git `v0.4.0-week4`.

**Deliverable:** Laporan akhir Week 4 dan tag rilis `v0.4.0-week4`.
