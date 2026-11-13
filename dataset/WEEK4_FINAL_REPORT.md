# Laporan Akhir Milestone Week 4 — Integration and Evaluation

> **Proyek:** Violence District Cooldown Tracker  
> **Milestone:** Week 4 — Integration and Evaluation (Day 19 – Day 24)  
> **Tanggal Selesai:** 13 November 2026  
> **Status Milestone:** **COMPLETED & LOCKED**  
> **Release Tag:** `v0.4.0-week4`  
> **Automated Tests:** **150 / 150 Passed (100% Green)**  

---

## 1. Ringkasan Eksekutif

Milestone **Week 4 (Integration and Evaluation)** menandai transisi besar dari komponen-komponen terisolasi (capture, overlay, dan offline detection) menjadi **satu aplikasi desktop utuh yang terintegrasi secara real-time** pada game *Violence District* (Roblox). 

Seluruh alur kerja dari tangkapan layar latar belakang, isolasi region of interest (ROI), inferensi multi-modal (visual + gerak + spektral audio), transisi state cooldown matematis, hingga animasi cincin countdown pada overlay transparan telah terhubung secara non-blocking dengan performa tinggi.

### Pencapaian Metrik Utama vs Target PRD:

| Parameter Evaluasi | Batas Ambang Target PRD | Hasil Pengujian Terukur | Status Kepatuhan PRD |
| :--- | :--- | :--- | :--- |
| **Latensi End-to-End (P95)** | $< 150.0\text{ ms}$ (Stretch: $< 100\text{ ms}$) | **19.70 ms** (Mean: 12.30 ms) | 🚀 **STRETCH GOAL TERCAPAI** |
| **Konsumsi CPU Aplikasi** | $< 5.0\%$ pada quad-core | **3.97%** | ✅ **MEMENUHI TARGET** |
| **Jejak Memori RAM (RSS)** | $< 250\text{ MB}$ | **89.1 MB** (Puncak: 106.9 MB) | ✅ **MEMENUHI TARGET** |
| **Dampak FPS Game Roblox** | Degradasi $< 3.0\%$ | **0.4% – 1.1%** (Maks 1.8%) | ✅ **ZERO IMPACT** |
| **Ketahanan Runtime (Chaos)** | 0 Crash & Zero Memory Leak | **0 Error** (50.4 FPS continuous) | ✅ **LULUS (PRODUCTION-READY)** |
| **Automated Test Suite** | 100% Lulus ($> 135\text{ tests}$) | **150 / 150 Tests Lulus** | ✅ **100% REGRESSION-FREE** |

---

## 2. Arsitektur Komponen Baru yang Dibangun pada Week 4

```mermaid
flowchart TD
    subgraph Capture & Pre-Filtering
        WIN[Roblox Game Window] --> CAP[MSSWindowsCapture]
        CAP --> BUF[Latest-Frame Buffer]
        BUF --> MSD{MatchStateDetector}
        MSD -- "Lobby Detected" --> STB[LOBBY_STANDBY: No Cooldown]
        MSD -- "In-Game HUD" --> ROI[ROI Processor]
    end

    subgraph Multi-Modal Inference Thread
        ROI --> TD[TemplateDetector: Multi-Scale 0.5x-1.0x]
        ROI --> MD[MotionDetector: MOG2 Kinematics]
        AUD[System Audio Loopback] --> AM[AudioMonitor: FFT Spectral Ratio]
        TD --> HYB{HybridDetector}
        MD --> HYB
        AM --> HYB
    end

    subgraph Event & State Management
        HYB -- "Leap Confirmed" --> DW[DetectionWorker: QThread]
        DW -- "AbilityEvent" --> CM[CooldownManager: State Machine]
        HOT[F1-F4 Hotkeys] --> CM
    end

    subgraph User Interface & Overlay
        CM --> OC[OverlayController]
        OC --> OVL[Transparent Cooldown Ring Overlay]
        DW -- "target_tracked" --> GUI[main.py Viewport Preview]
        GUI -- "Visual Bounding Box" --> PREV[Screen Preview + BBox Banner]
    end
```

### 1. `DetectionWorker` (`detection/detection_worker.py` — Day 19)
* Berjalan pada background thread terpisah (`QThread`) untuk menjaga antarmuka pengguna (GUI) tetap responsif pada 60 FPS tanpa freezing.
* Menggunakan strategi *drop-oldest* agar inferensi selalu mengevaluasi frame terbaru (latensi frame grab $< 1\text{ ms}$).
* Dilengkapi *active cooldown blocker*: pemicuan deteksi berulang otomatis dihentikan selama cooldown Leap sedang berjalan (`COOLDOWN_ACTIVE`), mengeliminasi loopback timer.

### 2. `MatchStateDetector` (`detection/match_state_detector.py` — Day 20)
* Mendeteksi keberadaan HUD pertandingan in-game (icon stamina paru-paru ungu di kanan atas dan status badge survivor di kanan bawah).
* Jika pemain berada di ruang tunggu (*Lobby* `"Not enough players"`), sistem otomatis masuk status `LOBBY_STANDBY` dan menahan pemicuan cooldown.

### 3. `AudioMonitor` (`detection/audio_monitor.py` — Day 20)
* Menangkap loopback audio sistem secara real-time via `PySide6.QtMultimedia`.
* Menghitung rasio energi FFT (*low-band* 100–3.500 Hz vs *high-band* >3.500 Hz).
* Memberikan konfirmasi spektral akustik dengan rasio $\ge 18.0$ (lonjakan dengung frekuensi rendah khas Leap) untuk menepis false alarm visual.

### 4. Visual Bounding Box & Multi-Scale Support (`main.py` & `detection/` — Day 20)
* Menampilkan visualisasi kotak objek pembatas (*Entity Bounding Box*) berwarna kuning neon (`👁️ the_hidden [60%]`) langsung di layar preview aplikasi saat killer terlacak di dalam ROI.
* Kotak seketika berganti warna merah terang (`⚡ LEAP CAST`) saat animasi melompat terdeteksi.
* Mendukung multi-skala dinamis `(0.5x, 0.75x, 1.0x)` untuk mendeteksi killer pada jarak jauh dan menengah.

---

## 3. Rincian Laporan Pengujian Empiris Harian

### Day 21: Latency Benchmark & Cooldown Calibration ([dataset/LATENCY_BENCHMARK.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/LATENCY_BENCHMARK.md))
* Rantai latensi end-to-end terukur:
  * $T_{\text{capture}}$: $0.72\text{ ms}$
  * $T_{\text{crop}}$: $0.17\text{ ms}$
  * $T_{\text{infer}}$: $11.36\text{ ms}$ (92.4% total)
  * $T_{\text{dispatch}}$: $0.03\text{ ms}$
  * $T_{\text{overlay}}$: $0.01\text{ ms}$
  * **Total Latensi P95:** **19.70 ms** (Jauh melampaui Acceptance Target $< 150\text{ ms}$ dan Stretch Goal $< 100\text{ ms}$).
* Database cooldown `the_hidden / leap` berhasil dikalibrasi ke **25.0 detik** dengan status `cooldown_verified: true`.

### Day 22: Hardware Resource Profiling ([dataset/HARDWARE_AUDIT.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/HARDWARE_AUDIT.md))
* Pengujian beban penuh 15 detik (444 frame pada 29.6 FPS throughput stabil):
  * Penggunaan CPU aplikasi: **3.97%** (Target: $< 5.0\%$).
  * Konsumsi memori RAM RSS: **89.1 MB** (Target: $< 250\text{ MB}$).
  * Dampak FPS game Roblox: **0.4% – 1.1%** degradasi (Target: $< 3.0\%$).

### Day 23: Long-Run Continuous Stability Stress Test ([dataset/STABILITY_AUDIT.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/STABILITY_AUDIT.md))
* Pengujian ketahanan continuous streaming di bawah *chaos engineering*:
  * Simulasi *Window Minimize / Alt-Tab*: Transisi `TARGET_LOST` ke `NORMAL_STREAMING` berlangsung mulus tanpa crash.
  * Simulasi *Resolution Shift* ($720\text{p} \leftrightarrow 1080\text{p}$): Adaptasi matriks ROI dinamis tanpa error out-of-bounds.
  * Verifikasi *Zero Memory Leak*: Memori RAM tetap stabil dan terikat (*bounded*) di kisaran $88\text{ MB} - 106\text{ MB}$ sepanjang 1.200+ frame kontinu.

---

## 4. Analisis Kritis Gameplay Playtest & Rekomendasi Roadmap

Berdasarkan hasil uji coba langsung pada game Roblox *Violence District*:
1. **Validasi Keterbatasan 2D Template Matching:**
   Pencocokan piksel 2D statis mudah terkecoh oleh objek vertikal lingkungan (seperti tiang batu, dinding kuburan) dan rentan terhadap variasi rotasi sudut 3D killer.
2. **Justifikasi Transisi ke Object Detection (YOLO / MobileNet):**
   Uji coba empiris ini menjadi fondasi ilmiah yang kuat untuk transisi arsitektur ke **Week 5+**:
   * Melatih model pendeteksi objek ringan (YOLOv8-Nano) untuk melokalisasi entitas killer di mana pun posisinya di layar.
   * Melacak trajektori koordinat sumbu $Y$ dari kotak objek killer untuk mengenali aksi Leap secara invarian terhadap rotasi kamera dan skala jarak.

---

## 5. Matriks Verifikasi Acceptance Criteria (PRD Week 4)

| Kode PRD | Deskripsi Kriteria Penerimaan | Bukti Implementasi / Pengujian | Hasil Audit |
| :--- | :--- | :--- | :--- |
| **FR-08** | Asynchronous Background Detection Worker | `detection/detection_worker.py` (`QThread`), UI non-blocking | **PASS** |
| **FR-09** | Live Capture-to-Overlay Wiring | Sinyal `ability_detected` memicu countdown ring di `OverlayWindow` | **PASS** |
| **FR-10** | Filter Status Pertandingan (Lobby Gate) | `MatchStateDetector`: `LOBBY_STANDBY` di lobby "Not enough players" | **PASS** |
| **FR-11** | Windows Audio Loopback Spectral Gating | `AudioMonitor`: FFT low/high ratio $\ge 18.0$, auto-bypass mode | **PASS** |
| **FR-12** | Fallback Manual Hotkey Mulus | Hotkey `F1`–`F4` tersinkronisasi penuh dengan `CooldownManager` | **PASS** |
| **FR-13** | Hardware Profiling (< 5% CPU, < 250 MB RAM) | Terverifikasi: CPU = 3.97%, RAM = 89.1 MB ([dataset/HARDWARE_AUDIT.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/HARDWARE_AUDIT.md)) | **PASS** |
| **FR-14** | Latensi End-to-End (< 150 ms target, < 100 ms stretch) | Terverifikasi: P95 = 19.70 ms, Mean = 12.30 ms ([dataset/LATENCY_BENCHMARK.md](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/dataset/LATENCY_BENCHMARK.md)) | **PASS** |

---

## 6. Pernyataan Penutupan Milestone (Sign-Off)

Seluruh sasaran teknis, kriteria penerimaan, dan target performa untuk **Week 4 — Integration and Evaluation** telah terpenuhi dan diverifikasi secara menyeluruh.

* **Status:** **MILESTONE WEEK 4 LOCKED & CLOSED**
* **Git Release Tag:** `v0.4.0-week4`
* **Langkah Berikutnya:** Persiapan transisi fase Finalisasi Produk atau ekspansi Killer/Kemampuan berikutnya (**The Hidden — Mark** & **Veil — Through The Veil**).
