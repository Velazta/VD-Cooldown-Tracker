# Risk & Assumption Register — Violence District Cooldown Tracker

Dokumen ini mencatat seluruh risiko teknis dan asumsi rekayasa perangkat lunak yang diambil selama pengembangan.  
Setiap entri diberi ID unik berbasis tanggal untuk mempermudah pelacakan, peninjauan berkala, dan verifikasi.

---

## 1. Risk Register (Daftar Risiko)

| ID | Tanggal Dicatat | Kategori | Deskripsi Risiko | Severity | Likelihood | Status | Rencana Mitigasi |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-20261111-01** | 2026-11-11 | Concurrency | Worker capture thread mengalami deadlock atau crash saat penutupan aplikasi (clean shutdown gagal). | High | Medium | Open | Menggunakan explicit stop event (`threading.Event`), batas timeout join (2.0 detik), dan intercept `closeEvent` di Qt. |
| **RSK-20261111-02** | 2026-11-11 | Memory | Akumulasi frame buffer menyebabkan memory leak jika frame tidak segera didaur ulang oleh garbage collector. | High | Low | Mitigated | Menggunakan `LatestFrameBuffer` berbasis `collections.deque(maxlen=1)` dengan penguncian thread-safe (`threading.Lock`). |
| **RSK-20261111-03** | 2026-11-11 | Capture | Window target diminimalkan (minimized) atau berpindah display monitor saat capture aktif. | Medium | High | Open | Menambahkan validasi `IsIconic(hwnd)` dan pengecekan bounds frame secara periodik, fallback ke status *Paused/Target Lost*. |
| **RSK-20261111-04** | 2026-11-11 | Platform | Anti-cheat atau pembaruan client Roblox memblokir / membatasi screen capture GDI/BitBlt. | High | Low | Open | Hanya menggunakan Windows Public API standar tanpa intervensi process memory. Backend dibuat modular agar bisa switch ke WGC jika GDI dibatasi. |
| **RSK-20261111-05** | 2026-11-11 | UI Thread | Pengolahan gambar atau konversi QImage memblokir event loop Qt sehingga GUI patah-patah / unresponsive. | High | Medium | Open | Memisahkan thread Capture/Processing dari UI thread. Pengiriman frame ke UI hanya menggunakan Qt Signals (`QImage` ringan). |

---

## 2. Assumption Register (Daftar Asumsi)

| ID | Tanggal Dicatat | Kategori | Deskripsi Asumsi | Status | Metode Verifikasi | Catatan / Hasil Verifikasi |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ASM-20261111-01** | 2026-11-11 | Environment | Python 3.14 (64-bit) dengan OpenCV 5.0 dan PySide6 6.12 kompatibel penuh untuk seluruh target Week 1. | **Verified** | Smoke test Day 1 & Day 2 | Terbukti berjalan stabil pada Day 1 & Day 2 tanpa kendala wheel. |
| **ASM-20261111-02** | 2026-11-11 | Capture | Backend MSS (Win32 BitBlt) mampu memenuhi target throughput 15–30 FPS dengan latensi < 150 ms. | **Verified** | Benchmark Day 2 | Terukur: Avg Latency **27.58 ms** pada **35.4 FPS** di resolusi 1920x1032. |
| **ASM-20261111-03** | 2026-11-11 | Display Mode | Roblox dijalankan pada mode Windowed atau Borderless Fullscreen (bukan Exclusive Fullscreen yang mengunci VRAM). | **Verified** | Pengujian Day 2 | Roblox terdeteksi dengan bounds `(0, 0, 1920, 1032)` dan visual tertangkap sempurna. |
| **ASM-20261111-04** | 2026-11-11 | DPI Scaling | Fungsi `DwmGetWindowAttribute` (bounds 9) akurat menghilangkan shadow window tanpa merusak koordinat ROI. | **Verified** | Validasi visual Day 2 | Frame `spike_test_frame.png` presisi 1:1 tanpa border hitam/transparan. |
| **ASM-20261111-05** | 2026-11-11 | Gameplay/HUD | Posisi ikon ability (HUD) The Hidden memiliki koordinat yang relatif stabil pada rasio layar 16:9. | **Unverified** | Observasi in-game Week 1 Day 4 | Akan diverifikasi saat kalibrasi ROI pada Day 4 dengan rekaman gameplay asli. |
| **ASM-20261111-06** | 2026-11-11 | Cooldown Data | Cooldown *Leap* milik The Hidden adalah 25 detik (nilai dasar awal dari PRD). | **Unverified** | Pengukuran in-game Week 3/4 | Nilai disimpan di JSON agar mudah diubah kapan saja tanpa ubah kode program. |
| **ASM-20261111-07** | 2026-11-11 | Performance | Konsumsi CPU aplikasi saat continuous capture berjalan tetap berada di bawah ambang 5% pada CPU modern. | **Unverified** | Pengujian Day 5 | Akan diukur dengan `psutil` / Performance Monitor pada Day 5. |
