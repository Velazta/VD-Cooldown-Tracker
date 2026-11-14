# Panduan Pelabelan Dataset YOLO (The Hidden Detector Rebuild)

Dokumen panduan standar anotasi dataset untuk **Violence District Cooldown Tracker** (Branch `feat/detector-rebuild`).

---

## 1. Skema Kelas (2 Kelas Entitas)

Detektor YOLO pada fase rebuild hanya bertugas **menemukan posisi entitas** di dalam frame ROI, **bukan** menentukan fase skill (fase skill dan pemicuan cooldown ditangani oleh Tracker & Kinematika Temporal).

| Class ID | Class Name | Deskripsi | Aturan Anotasi |
|:---:|:---:|:---|:---|
| `0` | **`hidden`** | Seluruh badan Killer **The Hidden** | Meliputi kepala, badan, tangan, dan kaki. Mencakup **seluruh 13 varian skin**, baik saat di tanah (*grounded*), berlari, maupun **sedang melayang di udara (*Leap airborne*)**. |
| `1` | **`survivor`** | Karakter **Survivor** (*Hard Negative*) | Karakter survivor perekam (sering tampak besar di tengah/depan) maupun survivor rekan. **Wajib dilabel** agar model terlatih membedakan survivor secara tegas dari killer. |
| *None* | *Background* | Lingkungan tanpa killer & survivor | File label dibiarkan kosong (`0 byte`). Valid sebagai negatif lingkungan (batu, dinding, efek visual). |

---

## 2. Aturan Bounding Box

1. **Box Ketat (*Tight Bounding Box*):**
   - Batas kotak harus pas mengelilingi tepi terluar karakter (ujung topi/kepala, ujung kaki, dan rentangan tangan/senjata).
   - Jangan menyertakan ruang kosong atau latar belakang berlebih di sekitar karakter.
2. **Objek Jauh & Kecil (*Small Objects*):**
   - Karakter The Hidden yang berada jauh di kejauhan (misalnya hanya setinggi 20–50 piksel di frame) **tetap wajib dilabel** dengan presisi.
   - Deteksi jarak jauh sangat krusial untuk memberikan peringatan dini sebelum Leap mendarat.
3. **Oklusi / Terhalang Objek (*Occlusion Rule*):**
   - Jika karakter terhalang tembok, pohon, atau pilar $\le 60\%$: **tetap beri label** pada bagian yang masih terlihat.
   - Jika terhalang $> 60\%$ (hampir tidak tampak / hanya secuil piksel samar): **lewati (jangan dilabel)** agar tidak membingungkan model.
4. **Satu Box per Karakter (*One Box per Instance*):**
   - Setiap killer atau survivor harus memiliki bounding box terpisah. Jangan menggabungkan dua karakter yang berdekatan ke dalam satu box.

---

## 3. Contoh Referensi Visual

### A. The Hidden — Pose Melayang di Udara (*Leap Airborne*)
Saat The Hidden melakukan Leap, ia melayang di udara dengan pose parabola meluncur (kaki terangkat/menekuk di udara):
- **Peach/Pink Skin (Mid-Air):** Karakter melayang bebas di atas tanah/batu. Seluruh badan di dalam kotak `class 0 (hidden)`.
  - Referensi: `docs/references/hidden_leap_airborne_peach1.png`
  - Referensi: `docs/references/hidden_leap_airborne_peach2.png`
- **Green Aura Skin + Fedora Hat (Mid-Air):** Karakter melayang dengan highlight hijau / topi fedora. Seluruh badan termasuk topi di dalam kotak `class 0 (hidden)`.
  - Referensi: `docs/references/hidden_leap_airborne_green_fedora.png`

### B. Survivor vs Killer (Pembedaan Mutlak)
- **Survivor:** Karakter berbaju biasa (misal baju putih, rambut survivor), tanpa aura killer, sering berada dekat kamera perekam $\rightarrow$ **Wajib `class 1 (survivor)`**.
- **Killer Lain / Spectator (misal Veil):** Bukan The Hidden. Jangan diberi label `0 (hidden)`!
- **Artifact Lingkungan (Batu, Pilar Gelap, Efek Hijau):** Jangan dilabel sebagai killer.

---

## 4. Alur Integrasi & Validasi Anotasi

1. Format koordinat YOLO: `<class_id> <x_center> <y_center> <width> <height>` (ternormalisasi 0.0 – 1.0).
2. Lokasi penyimpanan:
   - Gambar: `dataset/yolo/images/{train,val,test}/`
   - Label: `dataset/yolo/labels/{train,val,test}/`
3. Jalankan validasi integritas otomatis:
   ```bash
   python tools/validate_yolo_dataset.py
   ```
   Skrip ini memverifikasi bahwa seluruh koordinat valid, file label berpasangan, tidak ada label korup, dan menghasilkan `training/data.yaml`.
