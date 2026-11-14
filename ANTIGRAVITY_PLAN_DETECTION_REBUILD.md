# PLAN: Rebuild Deteksi Killer The Hidden (Leap & Mark)

Repo: `Velazta/VD-Cooldown-Tracker`, branch `dev`
Untuk: Antigravity (agent). Pemilik: Ravelin.
Status dokumen: berdasarkan audit repo `dev` (1 commit shallow). Hal yang **terverifikasi** ditandai ✅, **dugaan** ditandai ⚠️.

---

## 0. Cara kerja agent (WAJIB BACA DULU)

1. Baca berurutan: `AGENTS.md` → `ARCHITECTURE.md` → `PRD_WEEK_3.md` → `TODO.md` → file ini.
2. Kerjakan per **Phase**. Berhenti di setiap **🛑 CHECKPOINT** dan minta konfirmasi pemilik. Jangan lompat phase.
3. Task bertanda **👤 HUMAN** tidak bisa dikerjakan agent (merekam gameplay, melabel gambar, menjalankan training di GPU). Agent menyiapkan tooling, template, validator, lalu menunggu.
4. Jangan klaim "berhasil" tanpa menjalankan test/eval dan menempelkan outputnya. Semua angka metrik harus dari `tools/evaluate_pipeline.py` (Phase 6), bukan dari perkiraan.
5. Kerja di branch `feat/detector-rebuild` dari `dev`. Commit kecil per task. Test existing (suite saat ini) harus tetap hijau di setiap commit.
6. Dependensi baru: jelaskan alasannya dulu (aturan `AGENTS.md`), jangan install diam-diam. Lihat bagian 8.
7. Hanya capture layar dan input pasif. Dilarang membaca memori game, inject proses, atau hook. Cek ulang larangan di `AGENTS.md`.

---

## 1. Diagnosis (hasil audit)

### 1.1 Gejala dari pemilik
- Leap sering tidak terdeteksi.
- Objek asal ikut memicu countdown cooldown.
- Mark (skill Hidden) tidak terdeteksi walau sudah di-training.
- Hidden di ROI panel tracker muncul-hilang, walau sudah diberi gambar per skin, video gameplay, suara, PNG.

### 1.2 Akar masalah

| # | Temuan | Bukti | Status |
|---|--------|-------|--------|
| A | Label YOLO dibuat otomatis oleh MOG2 (blob gerak terbesar = "killer"), bukan label manusia | `tools/spatial_annotator.py` | ✅ |
| B | Video "survivor cam": figur besar di tengah adalah survivor perekam. Hidden **kecil dan jauh** (kira-kira 15 px di thumbnail 320 px lebar, sekitar 60 px di 1280 px). MOG2 memilih figur besar/bergerak, yaitu survivor, tembok, efek, HUD | contact sheet `hidden1_leap_skill.mp4`, `hidden1_mark_skill_hitsurvivor.mp4`; crop `dataset/extracted/killer_rois/` berisi tembok, orb hijau, kartu nama, survivor | ✅ |
| C | Hanya 487 dari 967 frame punya box. Frame tanpa box dianggap background oleh YOLO. Leap: 38 dari 133 frame (airborne 17/70, windup 8/25, landing 13/38) jadi "background" | `dataset/annotations/bounding_boxes.json` | ✅ |
| D | Mark tidak punya kelas. `CLASS_MAP` hanya kenal `leap_*`. `mark_*`, `chase_*`, `hit_*`, `idle`, `recovery` jatuh ke kelas 3 `negative`. 310 frame mark diajarkan sebagai "bukan skill" | `tools/spatial_annotator.py` | ✅ |
| E | Tidak ada kelas "badan Hidden". Hidden hanya dikenali kalau cocok fase tertentu | skema kelas 0–3 | ✅ |
| F | Data sangat kecil: 18 video, total 173,89 detik, 5 WAV. Box train: kelas 0=23, 1=7, 2=8, kelas 3=128 | `dataset/catalog.json`, label | ✅ |
| G | Frame diekstrak 10 fps. Windup Leap hanya 10–12 frame di 30 fps (sekitar 0,4 detik), jadi sekitar 4 frame saat diambil 10 fps | `dataset/temporal_annotations.json` | ✅ |
| H | PNG skin (52), WAV (5), PNG in-game tidak jadi label YOLO. Skin PNG hanya dipakai statistik warna, WAV hanya analisa FFT | `extract_dataset.py` hanya baca MP4 | ✅ |
| I | `trajectory_profiles.json` (parabola R² 0,54–0,80) dan template ROI (`template_builder.py`) dihitung dari box MOG2 yang salah. Klaim "terbukti" tidak valid | kedua tool membaca `bounding_boxes.json` | ✅ |
| J | Akurasi audio "100%" hanya dari 5 sampel, bukan bukti | `audio_inspection.json` | ✅ |
| K | Tidak ada kode inferensi, bobot, `data.yaml`, atau log training di `dev`. Validator multi-frame (Week 4) belum ada. Output mentah per frame langsung bisa menyalakan timer | pencarian repo | ✅ |
| L | Struktur folder: gambar di `extracted/{split}/{label}/x.jpg`, label di `extracted/labels/{split}/{label}/x.txt`. Ultralytics mencari label dengan mengganti `/images/` jadi `/labels/`. Path ini tak punya `images`, jadi label bisa tak ketemu dan semua frame dianggap background | konvensi Ultralytics, struktur repo | ⚠️ cek log training ("labels missing/empty") |
| M | Domain gap: video latih 1280×720 full-frame; live capture `1920×1032` lalu ROI `1280×780` di `(310,150)`. Skala Hidden di live ≈ 1,5× beda dari data latih | `config/app_config.json`, `catalog.json` | ⚠️ pastikan resolusi sumber rekaman |
| N | Video bernama `hidden1/2/3`, kemungkinan hanya sedikit skin dari 13 skin | `catalog.json` | ⚠️ cek |
| O | `CooldownManager` hanya memegang satu ability (`set_ability`), padahal Hidden punya Leap dan Mark | `cooldown/cooldown_manager.py` | ✅ |

### 1.3 Kesimpulan
Training "jelek" karena **data dan label**, bukan arsitektur YOLO. Perbaikan butuh: label manual yang benar, definisi kelas yang benar, data lebih banyak dan sesuai domain live, deteksi objek kecil, dan validasi temporal sebelum timer jalan. YOLO cukup dipakai untuk **menemukan posisi Hidden**. Keputusan "Leap/Mark terjadi" dibuat oleh tracker + recognizer + validator.

---

## 2. Tujuan, non-goal, target

**Tujuan**
- Deteksi Hidden stabil di ROI live untuk banyak skin dan jarak.
- Leap dan Mark memicu `AbilityEvent(source="vision")` hanya saat benar-benar terjadi.
- Tidak ada timer dari objek asal.

**Non-goal (fase ini)**
- Killer lain (Veil dll). Kerjakan Hidden dulu.
- Membaca memori game, hook, inject.
- Aplikasi mobile/web.

**Target awal (usulan, minta pemilik konfirmasi di Checkpoint 0)**
- Event-level Leap: recall ≥ 90%, precision ≥ 90% pada video uji yang tidak pernah dipakai latih.
- Event-level Mark: recall ≥ 70% (jarak dekat), precision ≥ 90%.
- False timer start ≤ 1 per 10 menit footage tanpa skill.
- Latensi dari frame ke event < 300 ms (target; ukur nyata).
- Inferensi tidak menurunkan FPS capture di bawah target `capture.target_fps` (30). Ukur.

---

## 3. Arsitektur target

```
Capture frame (windows_capture)
   └─ ROIProcessor (crop ROI sama seperti saat rekam data)
        └─ HiddenDetector (YOLO, kelas: hidden, survivor)
             └─ HiddenTracker (IoU/centroid, smoothing, hold N frame)
                  ├─ LeapRecognizer (kinematika: gerak vertikal + parabola, relatif ke survivor)
                  ├─ MarkRecognizer (sinyal dari Mark Signature Study, Phase 4)
                  └─ (opsional) AudioSensor, TemplateMatcher
                       └─ EventValidator (state machine, N-of-M, debounce, refractory)
                            └─ AbilityEvent(source="vision") → CooldownBank → Overlay
```

Prinsip:
- Detector hanya menjawab "di mana Hidden". Tidak ada kelas fase skill.
- Event hanya dari validator, tidak pernah langsung dari satu deteksi.
- Setiap trigger menulis alasan ke log (`logs/detections.jsonl`) supaya false positive bisa dibedah.
- Inferensi di worker thread, UI hanya menerima signal.

---

## PHASE 0 — Freeze & audit (hari 1)

**Tujuan:** hentikan pemakaian label salah, buat audit yang bisa diulang.

- **0.1** Buat branch `feat/detector-rebuild`.
- **0.2** Tulis `tools/audit_labels.py`:
  - hitung frame berlabel vs kosong per split/kelas/fase,
  - cek pasangan gambar↔label sesuai konvensi Ultralytics,
  - ekspor overlay (box digambar) ke `dataset/audit/overlays/` untuk review manusia,
  - laporkan komposisi kelas 3 per fase.
  - Test: `tests/test_audit_labels.py` (data sintetis kecil).
- **0.2b** Jalankan audit, simpan `dataset/DATA_AUDIT_REPORT.md` (angka dari bagian 1.2 harus cocok atau dijelaskan bedanya).
- **0.3** Pindahkan `dataset/annotations/bounding_boxes.json` dan `dataset/extracted/labels/` ke `dataset/legacy_mog2/` (jangan hapus). Beri README: "proposal kasar, BUKAN ground truth".
- **0.4** Ubah docstring `spatial_annotator.py`: output hanya *draft pre-annotation*. Hapus/ganti `CLASS_MAP` lama (default fallback ke kelas 3 adalah bug).
- **0.5** Tandai `trajectory_profiles.json` dan `dataset/templates/the_hidden/` sebagai **invalid sampai dibuat ulang dari label manual** (tambahkan `"status": "invalid_mog2_source"`).
- **0.6** Update `RISK.md` dan `TODO.md` dengan temuan A–O.

**Acceptance:** audit report ada; semua test lama hijau; tidak ada kode yang masih membaca label legacy tanpa peringatan.

🛑 **CHECKPOINT 0:** pemilik konfirmasi target (bagian 2) dan scope (Hidden saja).

---

## PHASE 1 — Rekam data sesuai domain live (hari 2–4)

### 1.1 👤 HUMAN: rekam footage baru
Rekam dengan jalur yang sama seperti live: window Roblox 1920×1032, simpan **sumber penuh** (OBS 1080p, 30 atau 60 fps), lalu ROI akan dipotong oleh tool dengan nilai `config/app_config.json`.

Checklist minimal (usulan; sesuaikan kemampuan):
- Skin: minimal 6 dari 13 skin. Catat `skin_id` per file.
- Jarak: dekat, menengah, jauh (Hidden kecil). Sengaja banyak yang jauh.
- Skill: minimal 20 kejadian Leap dan 20 Mark, dengan variasi map, cahaya, arah, ada/tidak ada survivor lain.
- Hasil Mark: kena, meleset, kena tembok.
- **Negatif (penting):** minimal 10 menit tanpa skill: Hidden jalan, chase, serangan biasa, vault, hit, Hidden terhalang, ruang kosong tanpa killer, survivor saja, killer lain (Veil) kalau ada.
- Penamaan: `hidden_skin{N}_{skill|neg}_{map}_{nomor}.mp4`.

### 1.2 Agent: extraction v2 (`tools/extract_dataset.py` versi baru atau `tools/extract_v2.py`)
- Terapkan **crop ROI yang sama persis** dengan live (baca `config/app_config.json`), tanpa resize berbeda dari pipeline live.
- Dalam jendela skill (dari `temporal_annotations`, ±1 detik): ambil di fps asli.
- Di luar jendela / negatif: ambil 2–5 fps.
- Buang near-duplicate (perceptual hash atau SSIM) supaya jumlah gambar tidak menipu.
- Simpan metadata per frame: video, frame index, skin_id, jarak (near/mid/far, diisi saat label), split.
- Struktur output sesuai Ultralytics: `dataset/yolo/images/{train,val,test}` dan `dataset/yolo/labels/{train,val,test}`.

### 1.3 Split by video (bukan by frame)
- `tools/make_splits.py` → `dataset/splits.json`.
- Test berisi video yang **tidak pernah** muncul di train/val. Sisihkan minimal 1–2 skin sebagai `test_unseen_skin` bila memungkinkan.
- Test otomatis: tidak ada video yang muncul di dua split.

### 1.4 Ground truth event
- Perluas `temporal_annotations.json` per video baru dengan `events: [{ability: "leap"|"mark", cast_start_frame: N, outcome: ...}]`.
- Tulis validator skema `tools/validate_temporal.py`.
- 👤 HUMAN mengisi `cast_start_frame` (agent boleh menyediakan scrubber OpenCV sederhana `tools/annotate_events.py`).

**Acceptance:** extraction berjalan end-to-end di video baru; split lolos test leakage; semua video punya event ground truth.

---

## PHASE 2 — Pelabelan manual (hari 4–7)

### 2.1 Skema kelas v2 (dikunci di `training/classes.yaml`)
- `0 hidden`: seluruh badan Hidden, **semua skin dan semua pose/fase**. Fase Leap/Mark **bukan** kelas.
- `1 survivor`: karakter survivor (negatif keras, termasuk survivor perekam di tengah layar).
- Frame tanpa keduanya: label kosong (valid, dihitung background).
- Opsional nanti (hanya jika studi Mark menunjukkan perlu): `mark_fx`.

Aturan label (tulis ke `docs/LABELING_GUIDE.md` dengan contoh gambar):
- Box ketat mengelilingi seluruh badan, termasuk kepala dan tangan.
- Hidden kecil tapi terlihat tetap dilabel.
- Terhalang > 60%: lewati dan catat sebagai `occluded`.
- Satu box per instance.

### 2.2 Pre-annotation + koreksi manusia
- Agent menyiapkan impor ke CVAT atau Label Studio (pilih yang gratis dan bisa dijalankan lokal; jelaskan pilihan).
- Pre-annotation boleh dari detektor umum atau MOG2 legacy, **hanya sebagai draft** yang wajib dikoreksi.
- 👤 HUMAN melabel/koreksi. Prioritas: frame jarak jauh dan frame skill.

### 2.3 Validator dataset (`tools/validate_yolo_dataset.py`)
Cek: setiap gambar punya file label (kosong hanya jika `declared_negative`), id kelas valid, koordinat 0–1, ukuran box minimum, box duplikat, pasangan path benar, tidak ada leakage video. Gagal = exit code ≠ 0.
Tulis `training/data.yaml` dari skrip, bukan manual.

### 2.4 Quality gate
- 👤 HUMAN review 100 overlay acak dari audit; benar ≥ 95% sebelum lanjut.
- Pedoman jumlah awal (heuristik, bukan target pasti; cek dokumentasi Ultralytics terbaru): ratusan sampai ribuan box `hidden` di train lintas ≥ 6 skin, dengan banyak sampel kecil/jauh.

🛑 **CHECKPOINT 2:** lapor jumlah gambar/box per split, per skin, per bucket ukuran (<32 px, 32–64 px, >64 px). Pemilik menyetujui sebelum training.

---

## PHASE 3 — Training detektor (hari 7–10)

### 3.1 Environment terpisah
- Buat `training/` dengan `requirements-train.txt` (ultralytics + torch). **Jangan** masuk `requirements.txt` aplikasi.
- ⚠️ Cek dukungan wheel PyTorch/Ultralytics untuk versi Python yang dipakai. Jika tidak ada, pakai venv Python lain atau Colab/Kaggle GPU. Agent harus memverifikasi sebelum install.
- Inferensi aplikasi: ekspor ONNX. Pilih runtime (`cv2.dnn` atau `onnxruntime`) setelah cek kompatibilitas dan kecepatan. Minta persetujuan (bagian 8).

### 3.2 Eksperimen terkontrol (`training/train_detector.py`)
Satu skrip, semua argumen di-log, seed tetap, hasil ke `runs/` (gitignored).

Matriks awal:

| Faktor | Nilai |
|--------|-------|
| Model | yolov8n / yolov8s (atau generasi Ultralytics yang aktif) |
| `imgsz` | 640, 960, 1280 |
| Strategi objek kecil | full frame vs crop zoom area tengah vs tiling/slicing saat inferensi |

Augmentasi: scale, HSV, mosaic aktif, flip horizontal boleh. Jangan augment berlebihan sampai Hidden hilang.

### 3.3 Komposit skin PNG (opsional, ablation)
- PNG skin sudah ber-alpha (4 channel; ⚠️ verifikasi alpha benar-benar transparan, bukan semua 255).
- `tools/synth_composite.py`: tempel skin ke background dari frame game nyata, skala acak termasuk kecil, posisi acak, blur/noise ringan.
- Batas: ≤ 20–30% gambar train, **tidak pernah** di val/test. Wajib ablation dengan vs tanpa komposit.

### 3.4 Hard-negative mining (2 putaran)
Jalankan detektor di footage negatif → kumpulkan false positive → 👤 label sebagai background/survivor → latih ulang.

### 3.5 Laporan
`training/REPORT.md`: mAP50, mAP50-95, **recall per bucket ukuran**, confusion matrix, galeri 30 kegagalan terburuk, perbandingan matriks eksperimen, model terpilih beserta alasannya.

**Acceptance:** keputusan model berbasis tabel eksperimen; recall `hidden` pada test (video baru) dilaporkan per jarak; tidak ada kelas selain `hidden`/`survivor`.

🛑 **CHECKPOINT 3:** pemilik review laporan. Jika recall `hidden` jauh dari target, kembali tambah data (Phase 1–2), bukan menambah kompleksitas model.

---

## PHASE 4 — Tracker & recognizer (hari 10–14)

### 4.1 `detection/hidden_tracker.py`
- Asosiasi IoU/centroid, smoothing, "hold" N frame saat deteksi hilang, ID stabil, riwayat `(t, cx, cy, w, h, conf)`.
- Hanya kelas `hidden` yang masuk tracker. `survivor` dipakai sebagai acuan posisi.
- Test unit dengan lintasan sintetis (hilang 2–3 frame, dua objek berpapasan).

### 4.2 Refactor kinematika
Pindahkan logika parabola dari `tools/trajectory_analyzer.py` ke modul bersama `detection/kinematics.py`. Hitung ulang profil dari **label manual** (output baru `dataset/trajectory_profiles_v2.json`).
- Kompensasi gerak kamera: ukur posisi Hidden **relatif ke survivor/ground** atau pakai optical flow latar. Kamera survivor bergerak, jadi koordinat piksel mentah menyesatkan.

### 4.3 `detection/leap_recognizer.py`
- Jendela geser ~0,5–1,0 detik: perpindahan vertikal, kecepatan, kecocokan parabola (R²), lonjakan skala box.
- Ambang disetel di train, divalidasi di val, dilaporkan sekali di test.
- Output: `candidate(leap, score, t_start)`.

### 4.4 Studi tanda Mark (`dataset/MARK_SIGNATURE_STUDY.md`) 👤+agent
Mark adalah tusukan ke depan, kemungkinan paling jelas saat dekat. Sebelum menulis recognizer:
- Analisa klip Mark berlabel: jarak Hidden ke survivor, pertumbuhan ukuran box, kecepatan maju, pose, efek hit, perbedaan dengan serangan biasa.
- Keputusan: (a) aturan kinematik + kedekatan, (b) tambah kelas `mark_fx`/pose jika ada tanda visual khas, atau (c) terima recall rendah di jarak jauh dan andalkan hotkey manual.
- Tulis keputusan beserta bukti angka. Jangan mengarang aturan sebelum studi ini.

### 4.5 `detection/mark_recognizer.py` sesuai keputusan 4.4.

### 4.6 Pembanding opsional
- `TemplateMatcher` (processing/template_matcher.py) pada area di sekitar box terlacak, setelah template dibuat ulang dari label manual. Simpan hanya jika menaikkan F1 di val.

**Acceptance:** recognizer berjalan offline pada box ground truth (batas atas) dan pada box hasil detektor (kenyataan); selisihnya dilaporkan.

---

## PHASE 5 — Validator, integrasi, multi-ability (hari 14–18)

### 5.1 `detection/event_validator.py`
State machine per ability: `IDLE → CANDIDATE → CONFIRMED → REFRACTORY`.
- Konfirmasi: N dari M frame (mulai usulan 3 dari 5, setel di val), skor minimal, track `hidden` sudah hidup ≥ K frame sebelum kandidat (mencegah objek asal).
- Refractory selama cooldown ability (dan reset manual).
- Emit **sekali** `AbilityEvent.create(..., source="vision", confidence=skor)`.
- Mendukung `cancel`.
- Test: urutan sintetis (noise, flicker, deteksi 1 frame) tidak boleh memicu.

### 5.2 Multi-ability
- `CooldownManager` saat ini satu ability. Buat `CooldownBank` (dict per `ability_id`) atau instansi per ability, backward-compatible dengan hotkey dan tombol simulasi.
- Overlay menampilkan Leap dan Mark. Perbarui `database/killerDatabase.json` (`detection_method`, bukan lagi `pose_sequence` generik; `cooldown_verified` tetap `false` sampai diukur di game).
- Test cooldown tetap hijau.

### 5.3 `detection/detector_service.py`
- Worker thread, buffer frame terbaru (drop frame lama, jangan antre tak terbatas).
- Signal Qt ke UI; tidak menyentuh widget dari thread worker.
- Toggle "Auto detect" di UI, **default mati**; mode debug menggambar box, ID track, state validator, skor.
- Ukur dan tampilkan ms inferensi di `PerformanceMonitor`.

### 5.4 Log keputusan
`logs/detections.jsonl`: timestamp, box, skor, state, alasan trigger. Tambah ke `.gitignore`. Panel debug: "kenapa timer mulai?"

**Acceptance:** replay video ke service menghasilkan event identik dengan evaluator offline (determinisme); UI tidak freeze; FPS terukur.

---

## PHASE 6 — Evaluasi (hari 18–20)

### 6.1 `tools/evaluate_pipeline.py`
Memutar ulang video lewat pipeline **identik** dengan live (ROI → detektor → tracker → recognizer → validator).
- Cocokkan event dengan ground truth (toleransi mulai usulan ±0,3 detik).
- Output: precision/recall/F1 per ability, false timer start per menit footage negatif, latensi, klip kegagalan.
- Laporan `dataset/WEEK3_EVAL_REPORT.md`.

### 6.2 Ablation
Detektor saja vs + tracker vs + validator vs + template/audio (bila ada).

### 6.3 👤 Uji live
10 match nyata; catat setiap trigger benar, terlewat, dan palsu (waktu + screenshot). Bandingkan dengan evaluator offline.

🛑 **CHECKPOINT 6:** lulus/tidak terhadap target bagian 2. Jika gagal, tulis analisis kegagalan (bucket jarak, skin, map) dan rencana tambah data. Jangan menurunkan ambang untuk memaksa lulus.

---

## PHASE 7 — Opsional: audio

Hanya dikerjakan jika evaluasi menunjukkan audio menambah nilai.
- Bukti sekarang tidak cukup (5 WAV). Kumpulkan ≥ 30 klip berlabel per kelas dari track audio video (ffmpeg tersedia di mesin audit; ⚠️ cek di mesin pemilik).
- Capture audio live butuh dependensi baru (loopback WASAPI). **Wajib persetujuan pemilik** dan penjelasan risiko.
- Catatan: suara skill killer hanya terdengar dalam jangkauan tertentu di game.

---

## PHASE 8 — Dokumentasi & rilis

- Update `README.md`, `ARCHITECTURE.md`, `RISK.md`, `TODO.md`, `docs/LABELING_GUIDE.md`.
- Dokumentasikan versi dataset (`dataset/DATASET_CARD.md`: jumlah per skin/jarak/split, tanggal, sumber).
- Tag rilis setelah Checkpoint 6 lulus.

---

## 7. Risiko baru (tambahkan ke `RISK.md`)

| Risiko | Mitigasi |
|--------|----------|
| Objek kecil dan jauh | imgsz tinggi, crop zoom/tiling, label banyak sampel jauh |
| Dataset kecil dan sedikit skin | rekam lebih banyak, split unseen-skin, komposit terbatas |
| Domain gap (resolusi/ROI) | rekam dan ekstrak dengan ROI live yang sama |
| Overfit ke sedikit video | split by video, uji di video baru |
| Mark sulit dideteksi di jarak jauh | studi Mark, terima batas, pertahankan hotkey manual |
| Kamera bergerak merusak kinematika | koordinat relatif ke survivor / optical flow |
| Latensi inferensi | worker thread, ONNX, drop frame, ukur FPS |
| Dependensi berat | environment training terpisah, runtime ringan di app |
| Patch game mengubah animasi/skin | versi dataset + regresi evaluator |

---

## 8. Keputusan yang butuh persetujuan pemilik sebelum agent lanjut

1. Dependensi training (ultralytics, torch) di environment terpisah, dan runtime inferensi (`cv2.dnn` vs `onnxruntime`).
2. Tool pelabelan (CVAT vs Label Studio) dan siapa yang melabel.
3. Target metrik di bagian 2.
4. Capture audio (Phase 7) ya/tidak.
5. Skema kelas v2 (`hidden`, `survivor`) dan aturan label.
6. Akses GPU untuk training (lokal, Colab, atau Kaggle).

---

## 9. Ringkasan tugas manusia

1. Rekam footage baru (skin, jarak, negatif banyak).
2. Isi `cast_start_frame` event.
3. Label dan koreksi box, review 100 overlay.
4. Jalankan training di GPU (atau minta agent menyiapkan notebook).
5. Uji live 10 match.
6. Setujui di setiap CHECKPOINT.

## 10. Prompt pembuka untuk Antigravity

> Baca `AGENTS.md`, `ARCHITECTURE.md`, `PRD_WEEK_3.md`, `TODO.md`, lalu `ANTIGRAVITY_PLAN_DETECTION_REBUILD.md`. Mulai dari Phase 0 di branch `feat/detector-rebuild`. Kerjakan satu phase, tampilkan bukti (output test, laporan audit), lalu berhenti di CHECKPOINT dan tunggu konfirmasi. Jangan install dependensi baru atau lanjut ke phase berikutnya tanpa persetujuan. Jangan klaim metrik tanpa menjalankan evaluator.
