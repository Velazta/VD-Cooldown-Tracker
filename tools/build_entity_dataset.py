"""Roblox 2-Class Entity Dataset Builder (The Hidden Killer vs Survivor).

Violence District Cooldown Tracker — Week 5 (Master Plan Execution)
Generates high-precision 2-class annotations:
Class 0: killer_the_hidden (All 52 skins, animations, poses, highlight shaders)
Class 1: survivor (Player avatar and survivor entities)
Plus hard negative background distractors (empty labels).
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "dataset" / "entity_yolo"

CLASS_NAMES = ["killer_the_hidden", "survivor"]


def apply_roblox_highlight(crop: np.ndarray, color: Tuple[int, int, int] = (0, 255, 60)) -> np.ndarray:
    """Menambahkan efek outline shader (Roblox Highlight) warna neon."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated = cv2.dilate(mask, kernel, iterations=1)
    outline = cv2.subtract(dilated, mask)

    out = crop.copy()
    out[outline > 0] = color
    out[mask > 0] = cv2.addWeighted(crop[mask > 0], 0.85, np.full_like(crop[mask > 0], color), 0.15, 0)
    return out


def clean_crop_alpha(img: np.ndarray) -> np.ndarray:
    """Memotong area transparan atau latar hitam pekat di sekitar karakter."""
    if img is None or img.size == 0:
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
        if w > 20 and h > 20:
            return img[y:y+h, x:x+w]
    return img


def build_entity_dataset(
    num_train_samples: int = 500,
    num_val_samples: int = 100,
    img_size: Tuple[int, int] = (640, 360),
) -> Path:
    """Membangun dataset 2-kelas bersih killer_the_hidden vs survivor."""
    print("Initializing Roblox 2-Class Entity Dataset Generation...")

    for split in ["train", "val"]:
        (OUTPUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 1. Kumpulkan Background Sources
    bg_sources: List[np.ndarray] = []
    # Distractor background
    distractor_dir = PROJECT_ROOT / "dataset" / "yolo_dataset" / "images" / "train"
    if distractor_dir.exists():
        for f in distractor_dir.glob("distractor_hard_bg_*.jpg"):
            bg_img = cv2.imread(str(f))
            if bg_img is not None:
                bg_sources.append(bg_img)

    # Background kuburan dari foto laptop user
    laptop_p = Path("C:/Users/Lenovo/.gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/.user_uploaded/media_1794577750549_553aadb4.jpg")
    if laptop_p.exists():
        l_img = cv2.imread(str(laptop_p))
        if l_img is not None:
            # potong area makam tanpa survivor
            bg_sources.append(l_img[80:500, 50:600])
            bg_sources.append(l_img[80:500, 600:1150])

    if not bg_sources:
        dummy_bg = np.zeros((720, 1280, 3), dtype=np.uint8)
        dummy_bg[:] = (30, 28, 24)
        bg_sources.append(dummy_bg)

    # 2. Kumpulkan CUTOUT ASLI THE HIDDEN SAJA (Membawa Pisau, Pink Blindfold, atau Topi Fedora)
    killer_cutouts: List[np.ndarray] = []

    # A. User-uploaded verified The Hidden images
    user_dir = Path("C:/Users/Lenovo/.gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/.user_uploaded")
    for up_name in [
        "media_1794581792709_641305e9.png", # The Hidden Green Leap (Top Hat & Knife)
        "media_1794581792710_b9f458d2.png", # The Hidden Pink Leap 1 (Blindfold & Knife)
        "media_1794581792712_2204fe7d.png", # The Hidden Pink Leap 2 (Blindfold & Knife)
        "media_1794577878322_e9a6d7c6.png", # The Hidden Green Leap 2
    ]:
        up_p = user_dir / up_name
        if up_p.exists():
            c = cv2.imread(str(up_p))
            if c is not None:
                killer_cutouts.append(clean_crop_alpha(c))

    # B. Verified The Hidden templates ASLI (HANYA yang membawa pisau, BUKAN survivor baju putih)
    t_hidden = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"
    for name in [
        "template_idle_pre_leap_var1.png",
        "template_idle_pre_leap_var2.png",
        "template_mark_solo_var1.png",
        "template_mark_solo_var2.png",
        "template_hit_wall_var1.png",
    ]:
        p = t_hidden / name
        if p.exists():
            c = cv2.imread(str(p))
            if c is not None:
                killer_cutouts.append(clean_crop_alpha(c))

    # C. Referensi pose The Hidden (Pink blindfold dengan pisau)
    ref_dir = Path("C:/Users/Lenovo/.gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/references")
    for rname in ["pose_case1_idle_stay.png", "pose_case4_mark_stab_db.png", "ref_case2_walk_chase.png"]:
        rp = ref_dir / rname
        if rp.exists():
            c = cv2.imread(str(rp))
            if c is not None:
                killer_cutouts.append(clean_crop_alpha(c))

    # D. Verified cutouts The Hidden dari dataset/killer_cutouts/ (termasuk leap2_0, leap3_0, mark5_1, mark6_1)
    k_dir = PROJECT_ROOT / "dataset" / "killer_cutouts"
    if k_dir.exists():
        for kp in k_dir.glob("*.jpg"):
            c = cv2.imread(str(kp))
            if c is not None:
                killer_cutouts.append(clean_crop_alpha(c))

    # 3. Kumpulkan SURVIVOR (TERMASUK BAJU PUTIH & VEIL SPECTATOR) SEBAGAI KELAS 1 (NEGATIF KERAS)
    survivor_cutouts: List[np.ndarray] = []
    
    # A. Survivor baju putih (dari leap4 dan template salah lama), laptop photos
    # Masukkan template lama yang salah (baju putih) ke kelas SURVIVOR agar model belajar ini BUKAN killer!
    for wrong_name in ["template_leap_airborne_var1.png", "template_leap_airborne_var2.png", "template_hit_survivor_var1.png"]:
        wp = t_hidden / wrong_name
        if wp.exists():
            wc = cv2.imread(str(wp))
            if wc is not None:
                survivor_cutouts.append(clean_crop_alpha(wc))

    surv_dir = PROJECT_ROOT / "dataset" / "survivor_cutouts"
    if surv_dir.exists():
        for sp in surv_dir.glob("*.png"):
            simg = cv2.imread(str(sp))
            if simg is not None and simg.shape[0] > 40 and simg.shape[1] > 20:
                survivor_cutouts.append(clean_crop_alpha(simg))

    # B. Veil / Spectator mode screenshots dari database (Negatif keras agar tidak disangka The Hidden)
    skin_dir = PROJECT_ROOT / "database" / "dataset" / "HIDDEN" / "PNG" / "SKIN"
    if skin_dir.exists():
        for sp in skin_dir.glob("*/*.png"):
            simg = cv2.imread(str(sp))
            if simg is not None:
                cropped = clean_crop_alpha(simg)
                if cropped is not None and cropped.shape[0] > 40 and cropped.shape[1] > 20:
                    survivor_cutouts.append(cropped)

    # 4. Kumpulkan Hard Negative Distractors (batu/tembok/tanah: leap2_1, leap3_1, leap3_2, mark5_0, mark6_0)
    hard_negatives: List[np.ndarray] = []
    hn_dir = PROJECT_ROOT / "dataset" / "hard_negatives"
    if hn_dir.exists():
        for hnp in hn_dir.glob("*.jpg"):
            himg = cv2.imread(str(hnp))
            if himg is not None:
                hard_negatives.append(himg)

    print(f"Dataset Assets: Killer Cutouts={len(killer_cutouts)}, Survivor Cutouts={len(survivor_cutouts)}, Hard Negatives={len(hard_negatives)}, Backgrounds={len(bg_sources)}")

    def generate_single_sample(split: str, sample_idx: int) -> None:
        bg_raw = random.choice(bg_sources)
        target_w, target_h = img_size
        canvas = cv2.resize(bg_raw, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # 12% probabilitas hard negative background (tanpa entitas sama sekali)
        if random.random() < 0.12:
            img_fn = f"sample_{split}_{sample_idx:04d}_distractor.jpg"
            lbl_fn = f"sample_{split}_{sample_idx:04d}_distractor.txt"
            cv2.imwrite(str(OUTPUT_DIR / "images" / split / img_fn), canvas)
            with open(OUTPUT_DIR / "labels" / split / lbl_fn, "w") as fp:
                pass
            return

        # Tempel hard negative distractor (batu, tembok, rumput) ke background tanpa label (agar model tidak false detect)
        if hard_negatives and random.random() < 0.40:
            hn_crop = random.choice(hard_negatives).copy()
            hnh, hnw = hn_crop.shape[:2]
            scale_hn = random.uniform(0.5, 1.2)
            nhnw = max(20, min(target_w - 20, int(hnw * scale_hn)))
            nhnh = max(20, min(target_h - 20, int(hnh * scale_hn)))
            hn_resized = cv2.resize(hn_crop, (nhnw, nhnh), interpolation=cv2.INTER_AREA)
            hn_x = random.randint(0, target_w - nhnw)
            hn_y = random.randint(0, target_h - nhnh)
            canvas[hn_y:hn_y+nhnh, hn_x:hn_x+nhnw] = hn_resized

        labels_to_write: List[str] = []

        # Tentukan skenario: 
        # - Skenario A (60%): Killer saja
        # - Skenario B (20%): Survivor saja (negatif keras)
        # - Skenario C (20%): Keduanya ada di satu frame (Killer mengejar/menyerang Survivor)
        r_scene = random.random()
        entities_to_place: List[Tuple[int, np.ndarray]] = []

        if r_scene < 0.60:
            entities_to_place.append((0, random.choice(killer_cutouts)))
        elif r_scene < 0.80 and survivor_cutouts:
            entities_to_place.append((1, random.choice(survivor_cutouts)))
        else:
            entities_to_place.append((0, random.choice(killer_cutouts)))
            if survivor_cutouts:
                entities_to_place.append((1, random.choice(survivor_cutouts)))

        for class_id, raw_cutout in entities_to_place:
            cutout = raw_cutout.copy()

            # Augmentasi Shader (untuk Killer): 50% kemungkinan Green/Red Outline Shader
            if class_id == 0 and random.random() < 0.50:
                color = (0, 255, 60) if random.random() < 0.80 else (0, 50, 255)
                cutout = apply_roblox_highlight(cutout, color)

            # Flip horizontal acak
            if random.random() < 0.50:
                cutout = cv2.flip(cutout, 1)

            ch, cw = cutout.shape[:2]
            # Skala entitas di layar (50px s/d 220px)
            target_kh = random.randint(50, min(220, target_h - 20))
            scale = target_kh / float(ch)
            target_kw = max(15, min(target_w - 20, int(cw * scale)))
            cutout = cv2.resize(cutout, (target_kw, target_kh), interpolation=cv2.INTER_AREA)

            # Posisi: Killer bisa di udara atau tanah; Survivor selalu di tanah
            if class_id == 0 and random.random() < 0.40:
                # Killer Leap di udara
                max_y = max(5, target_h - target_kh - 40)
                py = random.randint(5, max_y)
            else:
                # Di permukaan tanah
                min_y = max(5, int((target_h - target_kh) * 0.40))
                max_y = max(min_y, target_h - target_kh - 5)
                py = random.randint(min_y, max_y)

            max_x = max(5, target_w - target_kw - 5)
            px = random.randint(5, max_x)

            # Paste dengan alpha mask
            c_gray = cv2.cvtColor(cutout, cv2.COLOR_BGR2GRAY)
            _, c_mask = cv2.threshold(c_gray, 15, 255, cv2.THRESH_BINARY)
            roi = canvas[py:py+target_kh, px:px+target_kw]

            if roi.shape[:2] != cutout.shape[:2]:
                cutout = cv2.resize(cutout, (roi.shape[1], roi.shape[0]))
                c_mask = cv2.resize(c_mask, (roi.shape[1], roi.shape[0]))
                target_kw, target_kh = roi.shape[1], roi.shape[0]

            mask_inv = cv2.bitwise_not(c_mask)
            bg_part = cv2.bitwise_and(roi, roi, mask=mask_inv)
            fg_part = cv2.bitwise_and(cutout, cutout, mask=c_mask)
            canvas[py:py+target_kh, px:px+target_kw] = cv2.add(bg_part, fg_part)

            # Bounding box koordinat YOLO normalisasi
            xc = (px + target_kw / 2.0) / target_w
            yc = (py + target_kh / 2.0) / target_h
            nw = target_kw / float(target_w)
            nh = target_kh / float(target_h)
            labels_to_write.append(f"{class_id} {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}")

        img_fn = f"sample_{split}_{sample_idx:04d}.jpg"
        lbl_fn = f"sample_{split}_{sample_idx:04d}.txt"

        cv2.imwrite(str(OUTPUT_DIR / "images" / split / img_fn), canvas)
        with open(OUTPUT_DIR / "labels" / split / lbl_fn, "w") as fp:
            for line in labels_to_write:
                fp.write(line + "\n")

    print(f"Generating {num_train_samples} training samples...")
    for i in range(num_train_samples):
        generate_single_sample("train", i)

    print(f"Generating {num_val_samples} validation samples...")
    for i in range(num_val_samples):
        generate_single_sample("val", i)

    # dataset.yaml
    dataset_yaml_path = OUTPUT_DIR / "dataset.yaml"
    yaml_content = f"""path: {OUTPUT_DIR.as_posix()}
train: images/train
val: images/val
nc: {len(CLASS_NAMES)}
names: {CLASS_NAMES}
"""
    with open(dataset_yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"2-Class Entity Dataset generated at: {OUTPUT_DIR}")
    print(f"YAML config: {dataset_yaml_path}")
    return dataset_yaml_path


if __name__ == "__main__":
    build_entity_dataset(num_train_samples=500, num_val_samples=100)
