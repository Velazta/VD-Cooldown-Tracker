# PRD — Week 2: Cooldown State Machine & Transparent Overlay

**Proyek:** Violence District Cooldown Tracker  
**Milestone:** Week 2 — Aplikasi Desktop, Logika Cooldown & Overlay Transparan  
**Jadwal:** 16–22 November 2026  
**Stack Utama:** Python 3.14 (64-bit), PySide6, OpenCV, NumPy  
**Persistensi:** Konfigurasi & database JSON lokal yang sudah ada  
**Target Branch:** `dev`  
**Status:** Spesifikasi Eksekusi Terverifikasi  
**Prasyarat:** Week 1 Foundation & Technical Feasibility 100% Selesai & Lulus  

---

## 1. Serah Terima Week 1 dan Baseline Terverifikasi

Dokumen PRD ini disusun berbasiskan branch **dev** repositori saat ini. Seluruh checklist Week 1 pada `TODO.md` (Day 1 hingga Day 7) telah terverifikasi selesai beserta checklist akseptasinya.

### 1.1 Kemampuan yang Sudah Ada — Dilarang Membangun Ulang (Do Not Rebuild)

Fondasi teknis berikut telah beroperasi penuh pada branch `dev` dan **tidak boleh dibuat ulang**:

- Virtual environment Python, struktur proyek modular, logging terpusat (`VDTracker`), dan konfigurasi.
- Implementasi capture MSS/Win32 GDI BitBlt di balik abstraksi `BaseCaptureEngine`.
- Background capture worker, metadata frame (timestamp, resolusi, latensi), bounded latest-frame buffer (`maxlen=1`, drop-oldest), status capture, dan *clean-shutdown*.
- Aplikasi GUI PySide6 pada `main.py` dengan viewport live preview dan kontrol kalibrasi ROI.
- Model ROI, validasi batas (*boundary clamping*), pemotongan frame (*cropping*), bounding-box overlay, dan penyimpanan koordinat ke `config/app_config.json`.
- Mode preprocessing OpenCV: RAW, GRAYSCALE, CLAHE, THRESHOLD, dan CANNY.
- Baseline template matching ternormalisasi menggunakan `TM_CCOEFF_NORMED` yang aman dari zero-variance.
- Database Killer/kemampuan strongly-typed berbasis dataclass dengan validasi skema ketat di `database/database_manager.py`.
- Manajer konfigurasi runtime (`app/settings.py`) dan telemetri non-blocking (`monitoring/performance_monitor.py`) untuk FPS, latensi, CPU, dan RAM.
- Sebanyak 42 unit and integration tests yang lulus 100% via `pytest` dan `unittest`.

Tugas Week 2 adalah **memperluas dan me-refactor hanya pada bagian yang diperlukan**, bukan membangun ulang panel capture, kontrol ROI, database manager, atau performance monitor.

### 1.2 Keputusan Desain Penting dari Week 1

1. Aplikasi digunakan dari sudut pandang **Survivor POV**. Ikon ability Killer tidak tersedia pada HUD Survivor.
2. Target deteksi visual otomatis nantinya adalah **pose/aksi 3D Killer di viewport gameplay tengah layar**, bukan ikon cooldown di HUD.
3. Week 1 mencatat isu performa kritis: pemrosesan filter CLAHE pada area 1280×780 px memakan waktu ~54 ms/frame. Oleh karena itu, jangan aktifkan CLAHE secara default pada Week 2; evaluasi crop lokal/downscaling dialokasikan untuk Week 3.
4. Database telah mendukung field `trigger_type` seperti `on_cast_start` dan `on_release`. Logika cooldown Week 2 wajib memanfaatkan pembedaan ini.
5. Nilai durasi cooldown pada database berstatus unverified (`cooldown_verified: false`). Perlakukan sebagai data konfigurasi yang dapat diedit, bukan kebenaran mutlak dari game.
6. Penyelarasan label backend: label konfigurasi tertulis `windows_capture`, sedangkan kelas implementasi aktifnya adalah `MSSWindowsCapture`. Jangan mengganti backend yang sudah stabil hanya demi menyamakan label; selaraskan label/dokumentasi dengan implementasi riil.

### 1.3 Bukti Kinerja & Risiko Week 1 yang Tercatat di Repositori

Catatan resmi pada `RISK.md` dan laporan performa:
- Throughput capture MSS stabil pada 29.5–35.4 FPS dengan latensi capture 11.1–16.9 ms.
- RAM aplikasi stabil di kisaran 38.6–85.6 MB (jauh di bawah batas 250 MB).
- Penurunan FPS game terjadi saat pembacaan GDI 1080p penuh tanpa downsampling, yang telah diatasi melalui optimasi downscale OpenCV C++ sebelum dikirim ke Qt.
- Filter CLAHE memakan ~54 ms/frame pada area 1280×780 px.
- Clean shutdown, bounded ring buffer, penanganan `TARGET_LOST`, responsivitas UI, dan validasi JSON telah berstatus **Closed / Verified**.

---

## 2. Tujuan (Purpose)

Week 2 mentransformasikan purwarupa teknis Week 1 menjadi aplikasi pendamping desktop yang siap pakai, dilengkapi dengan jendela **Overlay Transparan independen** dan **Cooldown State Machine** yang presisi dan andal.

Alur integrasi utama:

$$\text{Aplikasi PySide6} \longrightarrow \text{Pilih Killer/Kemampuan} \longrightarrow \text{Trigger Manual / Simulasi} \longrightarrow \text{Cooldown State Machine} \longrightarrow \text{Overlay Transparan} \longrightarrow \text{READY}$$

Week 2 memvalidasi seluruh jalur timer dan overlay menggunakan kontrol simulasi/manual. Pengenalan pose visual otomatis Killer merupakan target Week 3/4, bukan target Week 2.

---

## 3. Sasaran Utama (Objectives)

Pada akhir Week 2:

1. Mempertahankan dan menyempurnakan aplikasi yang sudah ada tanpa menulis ulang dari nol.
2. Membangun modul *Cooldown State Machine* yang berdiri sendiri dan independen dari widget PySide6.
3. Memproses semantik `trigger_type` sesuai data masing-masing kemampuan (`on_cast_start` vs `on_release`).
4. Mengimplementasikan jendela overlay transparan yang melayang di atas layar secara independen (*Always-on-top*).
5. Menampilkan identitas kemampuan, progress lingkaran cooldown, hitungan mundur detik, dan status READY.
6. Menghubungkan database JSON lokal yang sudah ada ke seleksi cooldown.
7. Menyediakan tombol kontrol manual/simulasi untuk pengujian integrasi yang dapat diulang serta sebagai *fallback* Survivor.
8. Menguji penumpukan overlay (*stacking*), tembus klik (*click-through*), persistensi posisi, ketepatan waktu (*timing*), dan penutupan bersih pada environment Windows/Roblox riil.
9. Menyiapkan antarmuka kontrak event yang bersih (*event interface*) untuk modul deteksi visual Week 3.

---

## 4. Ruang Lingkup (Scope)

### 4.1 Dalam Lingkup (In Scope)

- Meninjau dan mempertahankan seluruh fitur capture, ROI, database, dan telemetri pada `main.py`.
- Refactor komposisi aplikasi seperlunya untuk memisahkan koordinasi UI dari logika bisnis timer.
- Cooldown Manager / State Machine yang berdiri sendiri (Python murni).
- Dukungan terhadap konfigurasi `trigger_type`: `on_cast_start`, `on_release`, dan nilai valid lainnya dari database.
- Seleksi kemampuan langsung dari `DatabaseManager` yang sudah ada.
- Kontrol trigger manual/simulasi untuk memicu event uji coba.
- Jendela overlay PySide6 yang transparan, tanpa bingkai (*frameless*), dan *always-on-top*.
- Pengaturan overlay yang dapat dikonfigurasi: visibilitas, posisi $(x, y)$, dimensi $(w, h)$, opasitas, dan preferensi *click-through*.
- Indikator circular/radial cooldown progress, teks sisa detik, nama kemampuan, dan transisi ke status READY.
- Persistensi pengaturan overlay melalui `SettingsManager` tanpa mencampur konfigurasi aplikasi ke dalam database killer.
- Unit tests, GUI integration tests, pengujian manual Windows, dan pembaruan dokumentasi.
- Antarmuka event netral (`AbilityEvent`) yang dapat dipanggil oleh detector Week 3 tanpa mengimpor kelas UI.

### 4.2 Luar Lingkup (Out of Scope)

- Deteksi otomatis Killer dan kemampuannya (*Leap*, *Mark*, *Through The Veil*).
- Training model YOLO, PyTorch, OCR, atau anotasi dataset visual.
- Klaim bahwa timer membaca state internal server game secara gaib.
- Timer simultan multi-slot/multi-killer (fokus pada single-slot aktif yang stabil terlebih dahulu).
- Sinkronisasi cloud, API online, atau pembuatan installer produksi `.exe`.
- Pembacaan memori proses game, injeksi DLL, hooking, executor API, modifikasi client Roblox, bypass anti-cheat, atau automasi bot/makro gameplay.

---

## 5. Alur Pengguna & Skenario Penggunaan (Use Cases)

| ID | Skenario Penggunaan | Hasil yang Diharapkan |
| :--- | :--- | :--- |
| **UC-W2-01** | Buka Aplikasi Tracker | Aplikasi capture/ROI terbuka dan memuat konfigurasi serta database tervalidasi. |
| **UC-W2-02** | Pilih Killer Aktif | Dropdown menampilkan Killer dari database yang sudah ada (`The Hidden`, `Veil`). |
| **UC-W2-03** | Pilih Kemampuan | Kemampuan yang aktif muncul dengan durasi cooldown dan status verifikasinya. |
| **UC-W2-04** | Tampilkan/Sembunyikan Overlay | Visibilitas overlay dapat dihidupkan/dimatikan secara independen dari panel utama. |
| **UC-W2-05** | Kalibrasi Posisi Overlay | Posisi, ukuran, dan opasitas overlay dapat diatur dan tersimpan permanen ke file config. |
| **UC-W2-06** | Simulasi Cast Start | Kemampuan bertipe `on_cast_start` langsung memulai cooldown saat event cast-start dikirim. |
| **UC-W2-07** | Simulasi Release | Kemampuan bertipe `on_release` masuk ke fase ancang-ancang dan baru mulai cooldown saat event release dikirim. |
| **UC-W2-08** | Reset/Batalkan Timer | Timer kembali ke kondisi awal (READY) secara deterministik. |
| **UC-W2-09** | Cooldown Selesai | Indikator overlay bertransisi ke status READY (lingkaran penuh, warna hijau neon). |
| **UC-W2-10** | Keluar dari Aplikasi | Overlay, timer UI, dan thread capture worker tertutup secara bersih tanpa proses menggantung. |

---

## 6. Kebutuhan Fungsional (Functional Requirements)

### FR-W2-01 — Mempertahankan Aplikasi & Pipeline Capture yang Ada
Aplikasi `main.py` yang ada saat ini telah menyediakan kontrol capture, preview visual, telemetri metrik, seleksi Killer, kalibrasi ROI, filter preprocessing, penyimpanan snapshot, dan integrasi settings/database.

Week 2 wajib:
- Mempertahankan seluruh kapabilitas tersebut selama proses integrasi.
- Menghindari penggantian jendela utama dengan purwarupa yang lebih minim fiturnya.
- Memastikan overlay dan timer cooldown tidak memblokir render preview capture atau event loop Qt.
- Memperbaiki hanya bug atau inkonsistensi yang telah terbukti lewat pengujian.

**Kriteria Akseptasi:**
- [ ] Tombol Start/Stop capture tetap berfungsi normal.
- [ ] Preview full-frame dan crop ROI tetap ter-update secara real-time.
- [ ] Dropdown seleksi Killer/database tetap berfungsi.
- [ ] Metrik capture dan telemetri sistem (CPU/RAM) tetap berjalan akurat.
- [ ] UI tetap responsif saat capture aktif bersamaan dengan overlay yang menyala.
- [ ] Tidak ada engine capture ganda yang berjalan di latar belakang.

---

### FR-W2-02 — Cooldown State Machine
Membangun modul terisolasi di bawah paket `cooldown/`, murni berbasis Python tanpa ketergantungan pada PySide6/Qt.

State minimum:
- `READY`: Tidak ada cooldown aktif; kemampuan siap digunakan.
- `WAITING_FOR_RELEASE`: Kemampuan bertipe `on_release` sedang dalam fase ancang-ancang/stance; timer cooldown belum mulai berjalan.
- `COOLDOWN`: Hitungan mundur cooldown sedang aktif.
- `DISABLED/INVALID`: Representasi error aman jika data kemampuan tidak valid atau dinonaktifkan.

Operasi yang wajib didukung:
- Memuat konfigurasi kemampuan berdasarkan `killer_id` dan `ability_id`.
- Menerima objek event ternormalisasi (`AbilityEvent`).
- Memulai cooldown hanya ketika event yang diterima cocok dengan `trigger_type` kemampuan.
- Menghitung sisa detik (`remaining_seconds`) dan rasio progress ternormalisasi (`0.0` hingga `1.0`).
- Menyediakan fungsi reset, cancel, dan clear state.
- Memberikan notifikasi perubahan status melalui callback/listener yang UI-agnostik.

Kebutuhan perhitungan waktu (Timing):
- Wajib menggunakan `time.monotonic()` untuk mencegah drift akibat perubahan jam sistem.
- Menghitung sisa waktu berbasis formula selisih: $\text{remaining} = \max(0.0, \text{end\_timestamp} - \text{time.monotonic()})$. Dilarang mengurangi variabel counter sebesar `0.033` setiap tick GUI!
- Mencegah event duplikat (*duplicate event suppression*) agar tidak me-restart timer yang sedang aktif berjalan.
- Memvalidasi durasi cooldown positif ($> 0.0$) dan status `enabled: true`.

Semantik Trigger:
- `on_cast_start`: Memulai cooldown seketika saat event `cast_start` diterima.
- `on_release`: Mengabaikan event awal atau masuk ke `WAITING_FOR_RELEASE`, dan baru memulai hitungan cooldown saat event `release` diterima.

**Kriteria Akseptasi:**
- [ ] Modul Cooldown Manager dapat diuji pada unit test tanpa menginisialisasi `QApplication` atau `QWidget`.
- [ ] Siklus transisi `READY` $\rightarrow$ `COOLDOWN` $\rightarrow$ `READY` bekerja sempurna.
- [ ] Trigger `on_cast_start` hanya terpicu pada event cast-start.
- [ ] Trigger `on_release` menunggu event release dan tidak memulai hitungan mundur terlalu dini.
- [ ] Event duplikat yang beruntun diabaikan dan tidak me-restart timer aktif.
- [ ] Perilaku reset/cancel berjalan deterministik.
- [ ] Perhitungan waktu terbukti akurat tanpa akumulasi jeda waktu (*zero clock drift*).

---

### FR-W2-03 — Antarmuka Kontrak Event Ternormalisasi (Normalized Ability Event)
Mendefinisikan kontrak data yang independen dari UI untuk mempermudah integrasi dengan modul deteksi visual pada Week 3.

Struktur model data:
```python
@dataclass
class AbilityEvent:
    killer_id: str
    ability_id: str
    event_type: str        # 'cast_start' | 'release' | 'cancel'
    timestamp: float       # time.monotonic()
    confidence: float = 1.0
    source: str = "manual" # 'manual' | 'hotkey' | 'vision'
```

Kebutuhan:
- Tombol kontrol manual di Week 2 memancarkan objek `AbilityEvent` yang sama persis dengan yang akan dihasilkan oleh AI detector di Week 3.
- Nilai `event_type` harus eksplisit (`cast_start`, `release`, `cancel`).
- Cooldown Manager tidak boleh mengimpor modul OpenCV atau mengetahui asal-usul event (apakah dari klik UI atau visi komputer).

**Kriteria Akseptasi:**
- [ ] Kontrol manual menghasilkan instance `AbilityEvent` yang valid.
- [ ] Cooldown Manager mengonsumsi event tanpa perlu tahu sumber asalnya.
- [ ] Modul deteksi Week 3 kelak dapat memanggil interface ini secara langsung tanpa mengubah kode rendering overlay.

---

### FR-W2-04 — Jendela Overlay Transparan (Transparent Overlay Window)
Membangun jendela PySide6 terpisah untuk menampilkan informasi melayang di atas layar.

Karakteristik teknis:
- Jendela tanpa bingkai (*frameless*) dengan latar belakang transparan penuh di luar area widget visual.
- *Always-on-top* melayang di atas game Roblox.
- Kontrol visibilitas independen (bisa ditutup/dibuka tanpa memengaruhi window utama).
- Posisi $(x, y)$, ukuran $(w, h)$, dan opasitas dapat disesuaikan.
- Mendukung mode *click-through* (`Qt.WA_TransparentForInput` / Win32 `WS_EX_TRANSPARENT`) agar klik mouse tembus ke gameplay Roblox.
- Dilarang menjalankan proses capture atau pengolahan citra di dalam metode render `paintEvent`.

**Kriteria Akseptasi:**
- [ ] Jendela overlay dapat dimunculkan dan disembunyikan secara independen.
- [ ] Area transparan memperlihatkan tampilan game di belakangnya tanpa kotak hitam.
- [ ] Perilaku *always-on-top* terverifikasi pada mode Windowed/Borderless Roblox.
- [ ] Posisi dan opasitas tersimpan ke file konfigurasi.
- [ ] Mode *click-through* teruji tidak menghalangi pergerakan kamera atau aksi klik pemain di dalam game.

---

### FR-W2-05 — Indikator Cooldown (Circular Progress Widget)
Overlay menampilkan satu indikator cooldown kemampuan aktif untuk MVP Week 2.

Tampilan visual:
- Nama Killer dan kemampuan yang sedang dipantau.
- Lingkaran progress radial (*circular progress ring*) yang berputar mundur dari 100% ke 0%.
- Teks angka sisa detik dengan presisi satu desimal (misal: `24.5s`, `12.0s`).
- Teks dan indikator warna berubah menjadi hijau neon terang bertuliskan `READY` saat cooldown usai.
- Indikator pembeda visual jika data cooldown berstatus unverified (`⚠️ Unverified`).

**Kriteria Akseptasi:**
- [ ] Pemicuan event secara visual memutar mundur lingkaran timer kemampuan yang tepat.
- [ ] Teks sisa detik ter-update mulus (refresh rate ~30–60 FPS).
- [ ] Animasi berakhir tepat waktu dan beralih ke status `READY`.
- [ ] Refresh GUI tidak me-restart atau mengganggu akurasi hitungan mundur.

---

### FR-W2-06 — Integrasi Database yang Sudah Ada
Memanfaatkan [database/killerDatabase.json](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/database/killerDatabase.json) dan `DatabaseManager` yang sudah dibangun pada Day 6.

Kebutuhan:
- Membaca daftar Killer dan kemampuan aktif langsung dari database.
- Mematuhi status `enabled: false`.
- Mengambil durasi cooldown dan tipe trigger langsung dari database tanpa hard-code di kode Python.
- Dilarang membuat skema file JSON tandingan atau mengubah struktur database yang ada tanpa izin.

**Kriteria Akseptasi:**
- [ ] Data *The Hidden* dan *Veil* termuat secara otomatis.
- [ ] Memilih kemampuan mengambil nilai durasi detik dan tipe trigger secara presisi.
- [ ] Perubahan angka cooldown pada file JSON langsung memengaruhi durasi timer tanpa perlu kompilasi ulang.

---

### FR-W2-07 — Persistensi Pengaturan Overlay
Memperluas model `AppConfig` dan `SettingsManager` pada [app/settings.py](file:///d:/KULIAH/CODINGAN/OverlayToolsVD/app/settings.py).

Pengaturan yang disimpan:
- Preferensi visibilitas overlay (`overlay_visible: bool`).
- Koordinat posisi overlay (`x`, `y`).
- Dimensi overlay (`width`, `height`).
- Opasitas overlay (`opacity: float`, rentang 0.2 – 1.0).
- Preferensi *always-on-top* dan *click-through*.

**Kriteria Akseptasi:**
- [ ] Pengaturan overlay termuat saat aplikasi dijalankan.
- [ ] Perubahan posisi dan opasitas tersimpan otomatis saat aplikasi ditutup.
- [ ] Konfigurasi capture dan ROI yang sudah ada tidak terganggu saat pengaturan overlay disimpan.

---

### FR-W2-08 — Manajemen Siklus Hidup & Penanganan Error
Aplikasi wajib:
- Menghentikan timer UI overlay saat aplikasi ditutup.
- Menyembunyikan/menutup overlay secara aman tanpa proses zombie.
- Menjaga kebersihan penghentian thread capture worker yang sudah ada.
- Mencegah inisialisasi timer ganda atau koneksi signal PyQt berulang-ulang.

**Kriteria Akseptasi:**
- [ ] Buka/tutup overlay berulang kali tidak menghasilkan window ganda di memori.
- [ ] Penutupan aplikasi saat cooldown sedang berjalan tertutup seketika tanpa error (*clean exit*).

---

## 7. Kebutuhan Non-Fungsional (Non-Functional Requirements)

| Kategori | Batasan & Standar Kebutuhan |
| :--- | :--- |
| **Akurasi Waktu** | Berbasis timestamp monotonic (`time.monotonic()`); deviasi akumulatif $< 50\text{ ms}$ sepanjang siklus. |
| **Responsivitas** | Event loop Qt utama tetap responsif ($\ge 30\text{ FPS}$) saat capture dan overlay aktif bersamaan. |
| **Overhead Performa** | Rendering overlay hanya menambah beban CPU minimal ($< 3\%$) dan RAM ($< 50\text{ MB}$). |
| **Manajemen Memori** | Tidak ada akumulasi riwayat frame atau event yang tidak dibatasi (*bounded memory usage*). |
| **Stabilitas** | Operasi buka/tutup dan trigger berulang kali terjamin bebas crash dan bebas memory leak. |
| **Kompatibilitas** | Windows 10/11 64-bit pada mode Borderless dan Windowed Roblox. |
| **Keamanan & Privasi** | 100% komputasi lokal, tanpa koneksi cloud, tanpa injeksi DLL/memori, tanpa makro input game. |

---

## 8. Arsitektur Modul & Batasan Tanggung Jawab (Module Boundaries)

Menggunakan modul yang telah ada dan menambahkan paket baru khusus Week 2:

```text
ViolenceDistrictTracker/
├── app/
│   ├── __init__.py
│   ├── logger.py               # (Week 1) Logging terpusat
│   ├── settings.py             # (Week 1/2) Diperluas untuk OverlaySettings
│   └── main_window.py          # (Week 2 Opsional) Refactor jendela kontrol utama
├── capture/                    # (Week 1) Capture engine & ring buffer (Tidak diubah)
├── processing/                 # (Week 1) ROI & filter CV (Tidak diubah)
├── database/                   # (Week 1) Killer & Ability persistence (Tidak diubah)
├── monitoring/                 # (Week 1) Telemetri hardware & FPS (Tidak diubah)
├── cooldown/                   # (Week 2 BARU)
│   ├── __init__.py
│   ├── ability_event.py        # Model data AbilityEvent ternormalisasi
│   ├── cooldown_state.py       # Enum status (READY, WAITING_FOR_RELEASE, COOLDOWN)
│   └── cooldown_manager.py     # State machine logika timer (UI-agnostik)
├── overlay/                    # (Week 2 BARU)
│   ├── __init__.py
│   ├── overlay_window.py       # Jendela transparan frameless always-on-top
│   ├── cooldown_widget.py      # Widget visual circular progress ring (QPainter)
│   └── overlay_controller.py   # Menghubungkan CooldownManager ke OverlayWindow
└── tests/
    ├── test_cooldown_manager.py
    ├── test_ability_event.py
    ├── test_overlay_settings.py
    └── test_cooldown_integration.py
```

Alur Data Week 2:
```text
Aplikasi Utama (main.py)
  ├── Engine Capture (Week 1) ──> FrameBuffer ──> ROI Processor (Week 1)
  ├── Database Manager (Week 1) ──> Konfigurasi Killer/Ability Terpilih
  └── Kontrol Tombol Manual ──> AbilityEvent (cast_start / release)
                                      │
                                      ▼
                            Cooldown State Machine (cooldown/)
                                      │
                                      ▼
                            Overlay Controller (overlay/)
                                      │
                                      ▼
                            Transparent Overlay Window (overlay/)
```

Aturan Batasan (*Boundary Rules*):
- `cooldown/` dilarang mengimpor modul Qt (`PySide6.QtWidgets`, dsb).
- `overlay/` dilarang mengambil alih siklus hidup capture engine.
- Jendela utama mengoordinasikan komponen, bukan memproses logika matematika timer secara langsung.
- Modul deteksi visi komputer Week 3 kelak hanya memancarkan `AbilityEvent`, tidak boleh langsung memanipulasi widget overlay.

---

## 9. Rencana Eksekusi Harian (Day 8 — Day 14)

### Day 8 — Handover Week 1 & Desain Kontrak Cooldown
- Verifikasi ulang seluruh regression test Week 1 pada branch `dev`.
- Bangun model data `AbilityEvent` dan enum status `CooldownState`.
- Definisikan semantik pemrosesan untuk `on_cast_start` dan `on_release`.
- Siapkan struktur modul paket `cooldown/` dan kerangka unit test-nya.
- **Deliverable:** Desain event/state terdokumentasi dan struktur modul Week 2 siap dikoding.

### Day 9 — Cooldown State Machine
- Bangun `cooldown/cooldown_manager.py` (state: `READY`, `WAITING_FOR_RELEASE`, `COOLDOWN`).
- Implementasikan perhitungan waktu monotonic (`time.monotonic()`).
- Implementasikan pencocokan event berdasarkan Killer ID, Ability ID, dan trigger type.
- Implementasikan penekanan event duplikat (*duplicate event suppression*) dan fungsi reset/cancel.
- **Deliverable:** Cooldown Manager mandiri yang teruji penuh via unit test.

### Day 10 — Fondasi Jendela Overlay Transparan
- Bangun `overlay/overlay_window.py` menggunakan PySide6.
- Terapkan flags: `FramelessWindowHint`, `WindowStaysOnTopHint`, dan background transparan.
- Terapkan pengaturan posisi $(x, y)$, ukuran, dan opasitas.
- Uji perilaku *click-through* pada desktop dan jendela Roblox.
- **Deliverable:** Purwarupa overlay transparan yang melayang di atas layar.

### Day 11 — Widget Indikator Cooldown (Circular Ring)
- Bangun `overlay/cooldown_widget.py` menggunakan `QPainter`.
- Gambar lingkaran radial progress yang berputar mundur secara halus.
- Tampilkan teks sisa waktu berformat `XX.Xs` dan transisi ke label `READY`.
- Hubungkan widget ke Cooldown Manager melalui `overlay/overlay_controller.py`.
- **Deliverable:** Overlay mampu menampilkan render status cooldown secara dinamis.

### Day 12 — Integrasi Kontrol Manual & Hotkey Fallback
- Tambahkan panel tombol uji simulasi (*Simulate Cast Start*, *Simulate Release*, *Reset*) pada GUI utama.
- Hubungkan seleksi Killer/kemampuan aktif ke penghasil `AbilityEvent`.
- Implementasikan listener hotkey manual (*F1* / *F2* fallback) agar Survivor bisa memicu timer saat Killer beraksi di luar jarak pandang kamera.
- Uji alur `on_cast_start` (*Leap*) dan `on_release` (*Through The Veil*).
- **Deliverable:** Alur penuh: Kontrol Manual $\rightarrow$ Cooldown Manager $\rightarrow$ Overlay Indicator.

### Day 13 — Persistensi Pengaturan Overlay & Uji Reliabilitas
- Perluas `app/settings.py` dengan model `OverlaySettings`.
- Simpan dan pulihkan posisi, ukuran, visibilitas, dan opasitas overlay ke `config/app_config.json`.
- Uji penanganan file konfigurasi rusak/hilang.
- Uji siklus hidup: buka/tutup aplikasi, minimalkan game, dan pastikan tidak ada kebocoran proses di latar belakang.
- **Deliverable:** Pengaturan overlay tersimpan permanen dan siklus aplikasi stabil 100%.

### Day 14 — Pengujian End-to-End, Benchmark Performa, & Review Week 2
- Jalankan demonstrasi end-to-end lengkap saat bermain Roblox.
- Uji input pass-through (pastikan klik mouse, WASD, dan mouse look berjalan 100% normal tanpa terhalang overlay).
- Ukur dampak performa CPU/RAM dan FPS game saat overlay aktif vs non-aktif.
- Update `TODO.md`, `ARCHITECTURE.md`, `RISK.md`, dan siapkan backlog dataset/deteksi untuk Week 3.
- **Deliverable:** Laporan performa Week 2 dan rilis tag `v0.2.0-week2`.

---

## 10. Kriteria Kelulusan Week 2 (Definition of Done)

Tugas Week 2 dinyatakan selesai hanya jika seluruh kriteria berikut terbukti lewat implementasi dan pengujian:

### Logika Cooldown
- [ ] Cooldown Manager bekerja independen dari modul UI/PySide6.
- [ ] Perhitungan waktu monotonic lolos unit test presisi.
- [ ] Semantik `on_cast_start` bekerja benar (langsung hitung mundur saat cast).
- [ ] Semantik `on_release` bekerja benar (menunggu pelepasan skill sebelum hitung mundur).
- [ ] Event duplikat tidak me-restart timer yang sedang berjalan.
- [ ] Fungsi reset dan pembatalan timer bekerja deterministik.
- [ ] Nilai database dan flag verifikasi terbaca dengan benar.

### Overlay
- [ ] Jendela overlay terpisah muncul transparan tanpa bingkai dan tanpa kotak hitam.
- [ ] Fitur *always-on-top* dan buka/tutup overlay teruji berjalan.
- [ ] Posisi, ukuran, dan opasitas dapat diatur dan tersimpan permanen.
- [ ] Fitur tembus klik (*click-through*) teruji tidak memblokir input game pemain.
- [ ] Indikator circular menampilkan nama kemampuan, sisa detik, progress ring, dan status READY.

### Integrasi & Stabilitas
- [ ] Seluruh fungsi capture, ROI, preview, dan database Week 1 tetap beroperasi normal.
- [ ] Event manual menggunakan format kontrak `AbilityEvent` yang sama dengan detector masa depan.
- [ ] Menutup aplikasi saat capture atau timer sedang aktif tetap menutup proses secara bersih (*clean exit*).
- [ ] Seluruh unit test Week 1 (42 tests) ditambah unit test baru Week 2 lulus 100%.
- [ ] Data perbandingan dampak performa CPU, RAM, dan FPS tercatat rapi di laporan pengujian.

---

## 11. Manajemen Risiko & Rencana Mitigasi Week 2

| Risiko Teknis | Potensi Dampak | Rencana Mitigasi |
| :--- | :--- | :--- |
| **Click-through Tidak Tembus ke Roblox** | Overlay menangkap klik mouse sehingga pemain tidak bisa menggerakkan kamera game. | Uji sedini mungkin (Day 10); kombinasikan atribut Qt dengan Windows API native `WS_EX_TRANSPARENT` via `SetWindowLong` jika diperlukan. |
| **Always-on-top Tertutup oleh Game** | Jendela overlay tenggelam di balik jendela Roblox. | Validasi mode tampilan Roblox yang didukung (Borderless/Windowed); evaluasi `SetWindowPos(HWND_TOPMOST)` jika Qt hint kalah prioritas. |
| **Timer Mengalami Akumulasi Jeda (Drift)** | Hitungan mundur 25 detik melar menjadi 28 detik karena delay tick GUI. | Kunci waktu selesai menggunakan timestamp monotonic absolut (`end_time = monotonic() + cd`), bukan decrement counter tick. |
| **Event Beruntun Me-restart Timer** | Spam klik manual atau noise deteksi visual me-reset hitungan mundur. | Pasang guard pada state machine: jika state sedang `COOLDOWN`, tolak event baru untuk kemampuan yang sama. |
| **Render Lingkaran Membebani CPU** | Animasi 60 FPS membuat preview capture patah-patah. | Batasi refresh timer overlay ke 30 FPS; gunakan operasi geometris sederhana pada `QPainter` tanpa komputasi berat. |
| **Pengaturan Capture Terhapus** | Menyimpan posisi overlay menimpa koordinat ROI yang sudah ada di config. | Perluas skema `app_config.json` secara modular di dalam `SettingsManager` dan lengkapi dengan unit test round-trip. |
| **Scope Creep ke Deteksi Otomatis AI** | Terjebak membuat model YOLO sehingga overlay tidak terselesaikan. | Jaga batasan scope: Week 2 hanya fokus pada timer dan overlay via kontrol manual/simulasi. Deteksi visual murni milik Week 3. |

---

## 12. Gerbang Kesiapan Menuju Week 3 (Week 3 Readiness Gate)

Week 3 (Perekaman Dataset Gameplay Survivor POV & Deteksi Aksi 3D Killer) baru diizinkan dimulai jika:
1. Pipeline capture dan ROI Week 1 tetap stabil tanpa regresi.
2. Event manual ternormalisasi berhasil menggerakkan Cooldown State Machine secara akurat.
3. Semantik `on_cast_start` dan `on_release` telah teruji valid secara otomatis maupun manual.
4. Overlay merender status sisa detik dan status READY dengan mulus di atas game Roblox.
5. Keterbatasan dan hasil pengujian tembus klik (*click-through*) terdokumentasi lengkap.
6. Aplikasi berjalan stabil tanpa kebocoran memori atau thread menggantung.
