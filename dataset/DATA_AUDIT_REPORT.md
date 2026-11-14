# DATA AUDIT REPORT — Legacy MOG2 Labels Audit

**Source File:** `D:\KULIAH\CODINGAN\OverlayToolsVD\dataset\annotations\bounding_boxes.json`  
**Total Frames:** 967  
**Frames With Bounding Box:** 487 (50.4%)  
**Empty Frames (Background):** 480 (49.6%)  

---

## 1. Verifikasi Temuan 1.2 Dokumen Master Plan

### Temuan C: Rasio Bounding Box pada Total Frame & Leap
- **Total Frame:** 967 frame | **Berisi Box:** 487 | **Kosong (Background):** 480
- **Rincian Fase Leap:**
  - `leap_windup`: total 25 frame (box: 17, kosong: 8)
  - `leap_airborne`: total 70 frame (box: 53, kosong: 17)
  - `leap_landing`: total 38 frame (box: 25, kosong: 13)
- **Total Frame Leap:** 133 frame (box: 95, kosong: 38)
- **Konfirmasi Status Temuan C:** âœ… Cocok persis (38 dari 133 frame Leap menjadi background).

### Temuan D: Komposisi Kelas 3 (Semua Non-Leap Masuk Kelas Negative)
Skema MOG2 `CLASS_MAP` lama hanya memetakan aksi `leap_*` ke kelas 0, 1, 2. Semua aksi lainnya jatuh ke kelas 3 (`negative`).
Rincian fase aksi yang dipaksa masuk ke Kelas 3:

| Fase Aksi Asli | Jumlah Frame di Kelas 3 | Dampak pada Model |
|---|---|---|
| `chase_running` | 180 | Dianggap negative |
| `idle_pre_leap` | 140 | Dianggap negative |
| `mark_solo` | 87 | Diajarkan sebagai BUKAN skill |
| `chase_and_mark` | 75 | Diajarkan sebagai BUKAN skill |
| `recovery_post_leap` | 74 | Dianggap negative |
| `hit_survivor` | 57 | Dianggap negative |
| `mark_pre_combo` | 53 | Diajarkan sebagai BUKAN skill |
| `mark_hit_survivor` | 48 | Diajarkan sebagai BUKAN skill |
| `mark_miss` | 47 | Diajarkan sebagai BUKAN skill |
| `hit_wall` | 45 | Dianggap negative |
| `hit_air` | 28 | Dianggap negative |

- **Total Frame Kelas 3:** 834 frame.
- **Konfirmasi Status Temuan D:** âœ… Terbukti (Aksi Mark sebanyak 310 frame diajarkan sebagai 'bukan skill').

### Temuan L: Pelanggaran Konvensi Ultralytics Pasangan Gambar <-> Label
- **Status:** âš ï¸ Terkonfirmasi Gagal
- **Kegagalan Resolusi Path:** 967 dari 967 frame.
- **Penyebab:** Path gambar menggunakan `extracted/{split}/{label}/x.jpg` tanpa folder `/images/`. Konvensi Ultralytics mencari label dengan mengganti string `/images/` menjadi `/labels/`. Karena `/images/` tidak ada di path, Ultralytics tidak menemukan label dan menganggap seluruh frame sebagai background.

---

## 2. Distribusi per Split Dataset

| Split | Total Frame | Berisi Box | Kosong (Background) | % Berisi Box |
|---|---|---|---|---|
| `train` | 324 | 166 | 158 | 51.2% |
| `val` | 302 | 144 | 158 | 47.7% |
| `test` | 341 | 177 | 164 | 51.9% |

## 3. Distribusi per Kelas ID Lama

| Kelas ID | Nama Kelas MOG2 | Total Frame | Berisi Box | Kosong |
|---|---|---|---|---|
| 3 | `negative` | 834 | 392 | 442 |
| 1 | `leap_windup` | 25 | 17 | 8 |
| 0 | `leap_airborne` | 70 | 53 | 17 |
| 2 | `leap_landing` | 38 | 25 | 13 |

## 4. Kesimpulan Audit
1. Label MOG2 tidak dapat dipakai sebagai Ground Truth karena kontaminasi survivor/tembok dan hilangnya label pada sebagian besar frame skill.
2. Konvensi Ultralytics dilanggar oleh struktur folder lama, menyebabkan frame dianggap background kosong saat training.
3. Semua artefak MOG2 harus dipindahkan ke `dataset/legacy_mog2/` dan tidak boleh diakses oleh pipeline produksi.