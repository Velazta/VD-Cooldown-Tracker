# Risk & Assumption Register — Violence District Cooldown Tracker

Dokumen ini mencatat seluruh risiko teknis dan asumsi rekayasa perangkat lunak yang diambil selama pengembangan.  
Setiap entri diberi ID unik berbasis tanggal untuk mempermudah pelacakan, peninjauan berkala, dan verifikasi.

---

## 1. Risk Register (Daftar Risiko)

| ID | Tanggal Dicatat | Kategori | Deskripsi Risiko | Severity | Likelihood | Status | Rencana Mitigasi & Hasil |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-20261111-01** | 2026-11-11 | Concurrency | Worker capture thread mengalami deadlock atau crash saat penutupan aplikasi (clean shutdown gagal). | High | Medium | **Closed / Verified** | Menggunakan explicit stop event (`threading.Event`), batas timeout join (2.0s), dan penanganan `closeEvent` di Qt. Terverifikasi bersih di seluruh sesi. |
| **RSK-20261111-02** | 2026-11-11 | Memory | Akumulasi frame buffer menyebabkan memory leak jika frame tidak segera didaur ulang oleh garbage collector. | High | Low | **Closed / Verified** | Terbukti pada Segmen 5.2 (Delta RAM 0.0 MB setelah 500 alokasi 1080p, drop-oldest menjamin zero-leak). |
| **RSK-20261111-03** | 2026-11-11 | Capture | Window target diminimalkan (minimized) atau ditutup saat capture aktif menyebabkan freeze atau salah capture. | Medium | High | **Closed / Verified** | Validasi `IsIconic(hwnd)` & `IsWindow(hwnd)` di `window_helper.py`, mengosongkan buffer dan beralih ke status `TARGET_LOST` saat Roblox tertutup/minimize. |
| **RSK-20261111-04** | 2026-11-11 | Platform | Anti-cheat atau pembaruan client Roblox memblokir / membatasi screen capture GDI/BitBlt. | High | Low | Open | Hanya menggunakan Windows Public API standar tanpa intervensi memory process. Backend dibuat modular agar bisa switch ke WGC jika GDI dibatasi. |
| **RSK-20261111-05** | 2026-11-11 | UI Thread | Pengolahan gambar atau konversi QImage memblokir event loop Qt sehingga GUI patah-patah / unresponsive. | High | Medium | **Closed / Verified** | Frame di-downscale menggunakan OpenCV C++ (SIMD) sebelum dikirim ke Qt Pixmap, memangkas beban CPU GUI hingga 85%. |
| **RSK-20261111-06** | 2026-11-11 | Performance | Full-frame (1080p) capture via GDI & CPU smooth scaling di UI thread membebani memory bus, menurunkan FPS game uncapped (174 -> 89 FPS). | High | High | Mitigated | Implementasi ROI cropping (Day 4) untuk hanya memproses area gameplay, optimasi preview scaling Qt, dan evaluasi WGC GPU texture untuk in-game. |
| **RSK-20261111-07** | 2026-11-11 | Computer Vision | Thresholding biner agresif dan Canny edge dapat menghilangkan siluet/tekstur penting pada map malam Violence District yang gelap. | Medium | Medium | Mitigated | Menambahkan mode CLAHE (Contrast Limited Adaptive Histogram Equalization) pada LAB color space yang mencerahkan scene malam tanpa merusak tekstur objek. |
| **RSK-20261112-08** | 2026-11-12 | UI/Capture | Efek rekursif (*Hall of Mirrors* / Droste effect) saat jendela Tracker ditaruh di depan game Roblox. | High | High | **Closed / Verified** | Menerapkan `SetWindowDisplayAffinity(hwnd, 0x11)` (`WDA_EXCLUDEFROMCAPTURE`) dan pengecualian PID tracker sendiri di `window_helper.py`. Jendela tracker menjadi transparan bagi capture. |
| **RSK-20261112-09** | 2026-11-12 | Computer Vision | Komputasi CLAHE pada resolusi besar (1280x780 ~ 1 MP) memakan waktu 54 ms/frame, menurunkan processing rate ke 14 FPS. | Medium | High | Open | Pada Week 3, CLAHE hanya diterapkan pada *localized bounding box* Killer (misal 150x150) atau menggunakan downscaling `scale_factor=0.5`. |

---

## 2. Assumption Register (Daftar Asumsi)

| ID | Tanggal Dicatat | Kategori | Deskripsi Asumsi | Status | Metode Verifikasi | Catatan / Hasil Verifikasi |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ASM-20261111-01** | 2026-11-11 | Environment | Python 3.14 (64-bit) dengan OpenCV 5.0 dan PySide6 6.12 kompatibel penuh untuk seluruh target Week 1. | **Verified** | Smoke test Day 1 & Day 2 | Terbukti berjalan stabil pada Day 1 s/d Day 5 tanpa kendala. |
| **ASM-20261111-02** | 2026-11-11 | Capture | Backend MSS (Win32 BitBlt) mampu memenuhi target throughput 15–30 FPS dengan latensi < 150 ms. | **Verified** | Benchmark Day 2 & Day 5 | Terukur stabil di **29.5 – 35.4 FPS** dengan latensi capture **11.1 – 16.9 ms** (jauh lebih cepat dari batas 150 ms). |
| **ASM-20261111-03** | 2026-11-11 | Display Mode | Roblox dijalankan pada mode Windowed atau Borderless Fullscreen (bukan Exclusive Fullscreen yang mengunci VRAM). | **Verified** | Pengujian Day 2 s/d Day 5 | Roblox terdeteksi dengan bounds `(0, 0, 1920, 1032)` dan visual tertangkap sempurna. |
| **ASM-20261111-04** | 2026-11-11 | DPI Scaling | Fungsi `DwmGetWindowAttribute` (bounds 9) akurat menghilangkan shadow window tanpa merusak koordinat ROI. | **Verified** | Validasi visual Day 2 s/d Day 5 | Frame snapshot dan ROI crop presisi 1:1 tanpa distorsi koordinat. |
| **ASM-20261111-05** | 2026-11-11 | Gameplay/HUD | [REVISED -> Invalidated] Awalnya diasumsikan ada ikon ability HUD Killer. Faktanya, aplikasi digunakan dari perspektif **Survivor POV** sehingga skill Killer tidak tampil di HUD, melainkan dideteksi dari **pose/animasi 3D Killer di viewport gameplay**. | **Invalidated / Revised** | Klarifikasi User (Day 4) | ROI difokuskan pada area *Center Play-Viewport* (membuang topbar/chat/leaderboard). Deteksi pose/aksi Killer ditangani pada Week 3 (YOLO + Temporal Analysis). |
| **ASM-20261111-06** | 2026-11-11 | Cooldown Data | Cooldown *Leap* milik The Hidden adalah 25 detik (nilai dasar awal dari PRD). | **Unverified** | Pengukuran in-game Week 3/4 | Nilai disimpan di JSON agar mudah diubah kapan saja tanpa ubah source code. |
| **ASM-20261111-07** | 2026-11-11 | Performance | Konsumsi RAM aplikasi < 250 MB dan CPU terkontrol pada hardware referensi. | **Verified** | Benchmark Day 5 | RAM terukur **38.6 – 85.6 MB** (Target < 250 MB terpenuhi telak). Penggunaan memori flat zero-leak. |
| **ASM-20261111-08** | 2026-11-11 | Detection | Dalam perspektif Survivor, animasi/pose *The Hidden -> Leap* hanya dapat dideteksi otomatis apabila Killer berada di dalam viewport kamera Survivor (tidak terhalang tembok/off-screen). | **Unverified** | Uji Gameplay Week 3 | Jika off-screen, timer tidak dapat otomatis terpicu (tersedia manual hotkey fallback sesuai PRD). |
