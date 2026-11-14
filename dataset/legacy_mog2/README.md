# Legacy MOG2 Annotations & Labels

> **STATUS: PROPOSAL KASAR, BUKAN GROUND TRUTH**

## Peringatan
File anotasi dan label di dalam direktori ini dihasilkan secara otomatis menggunakan algoritma computer vision MOG2 (Background Subtraction) berdasarkan pergerakan piksel terbesar.

### Masalah Teridentifikasi:
1. **Bukan Anotasi Manusia:** Blob pergerakan terbesar otomatis dilabeli sebagai "killer".
2. **Kontaminasi Survivor & Background:** Pada rekaman Survivor POV, MOG2 kerap memilih tubuh survivor, dinding bergerak, efek proyektil, atau elemen HUD.
3. **Data Loss (49.6% Empty):** Hanya 487 dari 967 frame yang memiliki bounding box. Sebanyak 38 dari 133 frame skill Leap hilang dan diajarkan sebagai background kosong ke model.
4. **Bug Kelas 3 (Negative):** Seluruh aksi selain Leap (`mark_*`, `chase_*`, `hit_*`) dipaksa masuk ke kelas 3 (`negative`). 310 frame aksi Mark diajarkan secara keliru sebagai "bukan skill".

**DILARANG** menggunakan data di dalam folder ini sebagai Ground Truth produksi atau tolok ukur akurasi final.
Lihat `dataset/DATA_AUDIT_REPORT.md` untuk laporan audit kuantitatif lengkap.
