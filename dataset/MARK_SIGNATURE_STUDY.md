# Studi Tanda Visual & Kinematika Aksi Mark (The Hidden)

**Dokumen Analisis:** `dataset/MARK_SIGNATURE_STUDY.md`  
**Milestone:** Week 4 / Rebuild Phase 4 (Task 4.4)  
**Tujuan:** Menganalisis karakteristik visual dan kinematik skill **Mark** pada rekaman gameplay Violence District, membedakannya dari **Leap** dan **Serangan Biasa (Basic Attack)**, serta menentukan aturan implementasi pada `detection/mark_recognizer.py`.

---

## 1. Karakteristik Mekanika Skill Mark di *Violence District*

Berdasarkan analisis rekaman video (`hidden1_mark_skill_hitsurvivor.mp4`, `hidden1_mark_skill_nohitsurvivor.mp4`, `hidden2_mark_skill.mp4`, `hidden_chasing+mark_skill.mp4`, `hidden_mark_skill_ref2.mp4`):
- **Aksi Gerak:** The Hidden melakukan tusukan/serbuan horizontal lurus ke arah survivor.
- **Perbedaan dengan Leap:**
  - **Leap:** Menghasilkan lintasan parabola melayang di udara (*airborne vertical arc* dengan $R^2 \ge 0.50$ dan $\Delta y \ge 35\text{ px}$).
  - **Mark:** Lintasan relatif datar secara vertikal ($\Delta y < 20\text{ px}$), namun memiliki lonjakan laju ekspansi skala bounding box (*looming effect*) dan lonjakan kecepatan maju mendekati survivor.
- **Perbedaan dengan Serangan Biasa (Basic Hit):**
  - **Basic Hit:** Ayunan pisau biasa di tempat saat sudah menempel survivor, durasi $\approx 0.2\text{s}$, tanpa lonjakan jarak maju.
  - **Mark:** Serbuan cepat dari jarak menengah ($10-30\text{ studs}$) ke jarak dekat ($0-5\text{ studs}$) dalam rentang waktu $\approx 0.3-0.5\text{ detik}$.

---

## 2. Analisis Data Terukur (*Empirical Measurements*)

| Parameter Kinematik | Leap Skill | Mark Skill | Serangan Biasa (Basic Hit) | Gerak Jalan / Chasing |
|:---|:---:|:---:|:---:|:---:|
| **Lintasan Vertikal Parabola ($R^2$)** | $\mathbf{\ge 0.50}$ (Kuat) | $< 0.30$ (Datar) | $< 0.25$ (Datar) | $< 0.15$ (Acak) |
| **Rentang Vertikal ($\Delta y$)** | $\mathbf{> 0.035}$ (Melayang) | $\le 0.020$ | $\le 0.015$ | $\le 0.010$ |
| **Laju Ekspansi Bounding Box ($\Delta Area$)** | Bervariasi ($\approx 1.0\times - 1.2\times$) | $\mathbf{\ge 1.30\times}$ (Surge Maju) | $\le 1.10\times$ (Statis) | $\approx 1.0\times$ |
| **Jarak Relatif ke Survivor ($D_{rel}$)** | Bebas ($0.1 - 0.8$) | **Mendekat Cepat ($D \le 0.35$)** | Sangat Dekat ($D \le 0.10$) | Bebas |
| **Durasi Aksi Terukur** | $0.6 - 1.2\text{ s}$ | $\mathbf{0.3 - 0.5\text{ s}}$ | $0.2 - 0.3\text{ s}$ | Berkelanjutan |

---

## 3. Keputusan Desain (*Design Decisions*)

Sesuai arahan Task 4.4, keputusan implementasi detektor Mark:

1. **Aturan Kinematik + Kedekatan (Aturan Utama):**
   - Menggunakan kombinasi:
     1. **Non-Parabolic:** Memastikan bukan gerakan melayang di udara (menghindari tumpang tindih dengan Leap).
     2. **Looming Surge:** Laju pertumbuhan area bounding box $\frac{A_{latest}}{A_{initial}} \ge 1.25$ dalam jendela $0.3-0.5\text{ detik}$.
     3. **Survivor Proximity:** Jarak euclidian antara Killer dan Survivor anchor berada dalam rentang kedekatan aktif ($D \le 0.40$ ternormalisasi).
2. **Keterbatasan Jarak Jauh (*Graceful Degradation*):**
   - Pada jarak yang sangat jauh ($> 40\text{ studs}$), proyeksi perspektif 2D membuat serbuan Mark tampak identik dengan lari biasa. 
   - Oleh karena itu, vision detector difokuskan pada presisi tinggi pada jarak dekat–menengah (target precision $\ge 90\%$), sementara pemicuan jarak jauh didukung oleh fallback manual (hotkey) tanpa memicu timer palsu.
