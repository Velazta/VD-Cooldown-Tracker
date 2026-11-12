# Week 2 Development Backlog — Desktop Application & Transparent Overlay

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 2 — Desktop Application & Transparent Overlay  
**Periode:** 16–22 November 2026  
**Status:** **READY FOR EXECUTION**  
**Prerequisites:** Week 1 Foundation (Capture Engine, ROI Processor, Database Manager, & Settings Manager) **100% Verified**.

---

## 🎯 Target Utama Week 2
Membangun antarmuka desktop PySide6 yang lengkap, jendela **Transparent Overlay** yang melayang di atas game (*Always-on-top & Click-through*), widget indikator *circular cooldown*, dan modul **Cooldown Manager** lengkap dengan tombol pintas manual (*hotkey fallback*) yang terhubung langsung ke `database/killerDatabase.json`.

---

## 📅 Rencana Harian Week 2 (Day 8 — Day 14)

### Day 8 — Application Shell & Data Integration
- [ ] Refactor `app/application.py` sebagai orkestrator utama aplikasi.
- [ ] Hubungkan `SettingsManager` dan `DatabaseManager` ke UI utama.
- [ ] Bangun panel pemilihan Killer dinamis (Dropdown otomatis membaca `The Hidden`, `Veil` dari JSON).
- [ ] Tampilkan daftar kemampuan (*Leap*, *Mark*, *Through The Veil*) beserta durasi cooldown dan tipe trigger (`on_cast_start` / `on_release`).
- [ ] Kemampuan mengedit durasi cooldown killer langsung dari UI panel dan tersimpan ke JSON.

### Day 9 — Cooldown State Machine & Cooldown Manager
- [ ] Bangun modul `cooldown/cooldown_manager.py`.
- [ ] Implementasikan State Machine kemampuan: `READY`, `ACTIVE`, `COOLDOWN`.
- [ ] Gunakan monotonic clock (`time.monotonic()`) untuk perhitungan sisa waktu berlatensi nol tanpa drift.
- [ ] Implementasikan tombol pintas manual (*Hotkey Listener*, misal tombol `F1` / `F2` atau angka) agar pemain Survivor bisa memicu timer secara manual saat killer melakukan skill di luar jarak pandang kamera (off-screen fallback).
- [ ] Unit test State Machine di `tests/test_cooldown.py`.

### Day 10 — Transparent Frameless Overlay Window
- [ ] Bangun jendela overlay di `overlay/overlay_window.py`.
- [ ] Terapkan window flags: `Qt.FramelessWindowHint` dan `Qt.WindowStaysOnTopHint`.
- [ ] Terapkan atribut transparansi: `Qt.WA_TranslucentBackground`.
- [ ] Terapkan atribut klik tembus: `Qt.WA_TransparentForInput` (agar mouse klik menembus ke game Roblox).
- [ ] Terapkan proteksi `set_window_capture_invisible()` agar jendela overlay tidak ikut terekam oleh capture engine.
- [ ] Uji kompatibilitas klik tembus pada mode Windowed dan Borderless Roblox.

### Day 11 — Circular Cooldown Indicator Widget
- [ ] Bangun custom widget di `overlay/cooldown_widget.py` menggunakan `QPainter`.
- [ ] Render *Radial Circular Progress Ring* (lingkaran progress mundur dari 100% ke 0%).
- [ ] Render teks angka sisa detik berukuran proporsional (misal: `24.5s`, `12.0s`, `READY`).
- [ ] Terapkan transisi warna: Merah/Kuning saat Cooldown aktif, Hijau neon saat `READY`.
- [ ] Animasi halus berbasis timer 30–60 FPS.

### Day 12 — Overlay Controller & Position Calibration
- [ ] Bangun `overlay/overlay_controller.py`.
- [ ] Mode kalibrasi posisi: Mode geser (*Draggable*) saat aplikasi di-unlock untuk memindahkan letak lingkaran timer ke posisi layar yang paling nyaman bagi mata pengguna.
- [ ] Simpan posisi overlay (`x`, `y`) ke `config/app_config.json`.
- [ ] Dukungan multi-ability layout (posisi vertikal / horizontal jika killer memiliki lebih dari 1 skill).

### Day 13 — End-to-End Integration & Input Pass-Through Testing
- [ ] Integrasikan seluruh modul: Capture Viewport ↔ ROI ↔ Cooldown Manager ↔ Transparent Overlay.
- [ ] Uji coba bermain Roblox dengan overlay menyala: pastikan tombol WASD, Space, Klik Kiri/Kanan, dan Mouse Look beroperasi 100% lancar tanpa terganggu oleh overlay.
- [ ] Uji responsivitas overlay saat Roblox diminimalkan atau ditutup.

### Day 14 — Performance Benchmark & Week 2 Review
- [ ] Ukur konsumsi CPU dan RAM saat overlay aktif merender animasi lingkaran (< 3% CPU, < 120 MB RAM).
- [ ] Dokumentasikan hasil pengujian Week 2 ke `dataset/PERFORMANCE_REPORT_WEEK2.md`.
- [ ] Review persiapan Week 3 (Perekaman Dataset Gameplay & Model AI Deteksi Pose).

---

## 🛡️ Kriteria Lulus Week 2 (Definition of Done)
1. Jendela transparan muncul melayang di atas Roblox tanpa title bar dan tanpa border hitam.
2. Input mouse dan keyboard pemain tembus 100% ke game Roblox (*Click-through confirmed*).
3. Lingkaran cooldown berputar mundur dengan mulus dan menampilkan teks hitungan detik presisi.
4. Cooldown dapat dipicu secara manual via hotkey atau tombol panel.
5. Pilihan Killer dan Ability terikat langsung ke `database/killerDatabase.json`.
6. Tidak ada penurunan performa game yang signifikan.
