# End-to-End Latency Benchmark & Profiling Report

> **Milestone:** Week 4 — Integration and Evaluation (Day 21)  
> **Waktu Uji:** 2026-11-13 18:37:58  
> **Total Sampel:** 100 iterasi frame  
> **Environment:** Windows 64-bit | Pure Python & OpenCV C++ SIMD  

## 1. Ringkasan Eksekutif & Kepatuhan PRD

Pengukuran latensi menyeluruh (*end-to-end pipeline*) mencakup rantai proses lengkap:
$$\text{Latency}_{\text{total}} = T_{\text{capture}} + T_{\text{crop}} + T_{\text{infer}} + T_{\text{dispatch}} + T_{\text{overlay}}$$

| Metrik Target PRD | Batas Ambang | Hasil P95 Terukur | Hasil Rata-rata | Status Verifikasi |
| :--- | :--- | :--- | :--- | :--- |
| **Acceptance Target** | < 150.0 ms | **19.70 ms** | 12.30 ms | ✅ **MEMENUHI TARGET** |
| **Stretch Goal Target** | < 100.0 ms | **19.70 ms** | 12.30 ms | 🚀 **STRETCH GOAL TERCAPAI** |

## 2. Rincian Latensi per Tahapan Pipeline (Stage Breakdown)

| Tahapan Pipeline | Mean (ms) | Median (ms) | P90 (ms) | P95 (ms) | P99 (ms) | Min (ms) | Max (ms) | Kontribusi % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `T_capture (Frame Grab)` | 0.72 | 0.67 | 1.01 | 1.11 | 1.66 | 0.50 | 1.66 | 5.9% |
| `T_crop (ROI Extraction)` | 0.17 | 0.15 | 0.25 | 0.30 | 0.47 | 0.01 | 0.47 | 1.4% |
| `T_infer (Multi-Scale CV)` | 11.36 | 10.39 | 15.84 | 18.44 | 21.46 | 7.88 | 21.46 | 92.4% |
| `T_dispatch (Event & State)` | 0.03 | 0.03 | 0.04 | 0.05 | 0.07 | 0.02 | 0.07 | 0.2% |
| `T_overlay (Paint Prep)` | 0.01 | 0.01 | 0.02 | 0.02 | 0.04 | 0.01 | 0.04 | 0.1% |
| **TOTAL END-TO-END** | **12.30** | **11.34** | **16.74** | **19.70** | **23.14** | **8.67** | **23.14** | **100.0%** |

## 3. Analisis Teknis & Observasi Latensi

1. **Dominasi Tahap Inferensi Visual (11.36 ms):**  
   Inferensi multi-scale template matching merupakan kontributor terbesar latensi (~75–85% total waktu), namun berkat pemotongan ROI sebelum matching serta pre-cached template scaling, latensi tetap berada jauh di bawah 20 ms.

2. **Efisiensi Ekstraksi ROI (0.17 ms):**  
   Pemotongan NumPy slice array pada ROI hanya memakan waktu fraksi milidetik (< 0.5 ms), membuktikan pendekatan *ROI-first cropping* sangat efisien.

3. **Kecepatan State Transition & Dispatch (0.03 ms):**  
   Penerjemahan `DetectionResult` ke `AbilityEvent` dan transisi state pada `CooldownManager` berlangsung hampir instan (< 0.2 ms).

## 4. Kalibrasi Cooldown Database (The Hidden Leap)

- **ID Kemampuan:** `the_hidden / leap`
- **Durasi Terkalibrasi:** `25.0 detik`
- **Trigger Type:** `on_cast_start` (terpicu saat animasi melompat terdeteksi).
- **Status Kalibrasi:** Terverifikasi terhadap durasi in-game Violence District standar.

```json
{
  "killer_id": "the_hidden",
  "ability_id": "leap",
  "calibrated_cooldown_seconds": 25.0,
  "measured_p95_latency_ms": 19.7,
  "target_threshold_ms": 150.0,
  "status": "CALIBRATED_AND_VERIFIED"
}
```

## 5. Kesimpulan
- Latensi P95 terukur sebesar **19.70 ms**, berhasil melampaui Acceptance Target (< 150 ms) sekaligus melampaui Stretch Goal (< 100 ms).
- Sistem siap untuk pengujian beban sumber daya perangkat keras pada Day 22.
