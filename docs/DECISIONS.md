# Architectural Decision Records (ADR)

Dokumen ini mencatat keputusan arsitektural penting dalam pengembangan **Violence District Cooldown Tracker**.

---

## ADR-001: Pivot ke Pemicu Manual (Global Hotkey Companion)

- **Tanggal:** 14 November 2026
- **Status:** Diterima (Accepted)
- **Konteks:**
  - Evaluasi menyeluruh terhadap deteksi otomatis berbasis Computer Vision (OpenCV/YOLOv8) menunjukkan tingginya variasi visual lingkungan game, efek shader Roblox, pergerakan dinamis kamera survivor, serta keterbatasan dataset gameplay tanpa akses ke memori/state internal game.
  - Pengguna membutuhkan companion tool yang **100% andal**, tidak memicu false alarm objek asal, memiliki latensi instan (<10 ms), dan dapat digunakan secara mulus saat bermain game Roblox (*Roblox window in focus*).
  - Mekanisme hotkey lama (`F1`–`F4`) di `main.py` hanya bekerja ketika jendela aplikasi memiliki fokus GUI (`_handle_hotkey` via Qt window event filter). Ketika Roblox fokus, event keyboard tidak diterima aplikasi.
  - Durasi cooldown skill di database (`killerDatabase.json`) masih merupakan estimasi komunitas dan membutuhkan mekanisme kalibrasi/override oleh pengguna tanpa merusak file database bawaan.

- **Keputusan:**
  1. **Fokus Utama:** Mengalihkan prioritas pengembangan dari deteksi visi otomatis ke **Manual Trigger Companion** (`ANTIGRAVITY_PLAN_MANUAL_TRIGGER.md`).
  2. **Backlog Deteksi Visi:** Seluruh task deteksi otomatis (YOLO, screen capture, audio analysis, replay pipeline) ditunda dan dipindahkan ke backlog (Phase M9).
  3. **Global Hotkey via Win32 `RegisterHotKey`:** Menggunakan API OS Win32 `user32.RegisterHotKey` dengan flag `MOD_NOREPEAT` melalui pustaka standar Python `ctypes`.
  4. **Native Qt Event Filter:** Menangkap pesan OS `WM_HOTKEY` (0x0312) langsung pada thread GUI utama menggunakan `QAbstractNativeEventFilter` dari PySide6, tanpa dependensi paket pihak ketiga (`pynput`, `keyboard`).
  5. **Zero-New-Dependencies:** Menghindari penambahan dependensi pihak ketiga untuk menjaga portabilitas dan mencegah pemicuan deteksi heuristic antivirus/anti-cheat.
  6. **Multi-Ability Cooldown:** Menggunakan `CooldownBank` untuk mengelola beberapa ability sekaligus secara independen (misalnya Leap dan Mark dapat menghitung mundur bersamaan).
  7. **User Overrides:** Nilai cooldown kustom disimpan terpisah di `config/user_overrides.json` dan digabungkan saat runtime dengan `database/killerDatabase.json`.
  8. **Optional Capture:** Modul screen capture dinonaktifkan secara default saat aplikasi dibuka (`capture.enabled_on_start: false`) untuk meminimalkan beban CPU/RAM.

- **Konsekuensi:**
  - **Positif:** Keandalan 100%, false positive 0%, latensi pemicuan instan (0–1 ms), penggunaan CPU/RAM sangat rendah saat bermain game (<1% CPU, <50 MB RAM), dan tanpa risiko pelanggaran anti-cheat Roblox (hanya API Windows pasif OS-level dan overlay transparan).
  - **Batasan:** Memerlukan input manual pengguna saat melihat killer menggunakan skill. Tombol hotkey yang didaftarkan ke OS akan dimakan (*consumed*) oleh OS sehingga tidak diteruskan ke Roblox; mitigasi dilakukan dengan memilih tombol default yang jarang/tidak dipakai game (Numpad 1, Numpad 2, Numpad 0) dan menyediakan rebind UI.
