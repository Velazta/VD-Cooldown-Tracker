"""Roblox Multi-Class Dataset Generator for The Hidden Killer & Actions.

Violence District Cooldown Tracker — Week 5 (Action Pose Retraining)
Generates high-precision multi-class annotations and augmented gameplay frames:
Class 0: hidden_grounded (Idle, Walk, Hit Attack with feet on ground)
Class 1: hidden_leap_airborne (Airborne mid-air leap with tucked legs)
Class 2: hidden_mark_stab (Horizontal stabbing knife thrust)
Plus hard negative background distractors (empty labels).
"""

from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "dataset" / "multiclass_yolo"

CLASS_NAMES = ["hidden_grounded", "hidden_leap_airborne", "hidden_mark_stab"]


def apply_roblox_highlight(crop: np.ndarray, color: Tuple[int, int, int] = (0, 255, 60)) -> np.ndarray:
    """Menambahkan efek outline shader (Roblox Highlight) warna neon."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated = cv2.dilate(mask, kernel, iterations=1)
    outline = cv2.subtract(dilated, mask)

    out = crop.copy()
    out[outline > 0] = color
    # sedikit tint transparan pada bagian badan
    out[mask > 0] = cv2.addWeighted(crop[mask > 0], 0.85, np.full_like(crop[mask > 0], color), 0.15, 0)
    return out


def extract_cutout(img_path: Path) -> np.ndarray:
    """Membaca citra dan memastikan format BGR."""
    return cv2.imread(str(img_path))


def build_multiclass_dataset(
    num_train_samples: int = 400,
    num_val_samples: int = 80,
    img_size: Tuple[int, int] = (640, 360),
) -> Path:
    """Membangun dataset multi-class teranotasi presisi tinggi."""
    print("Initializing Multi-Class Roblox Dataset Generation...")

    # Bersihkan output directory
    for split in ["train", "val"]:
        (OUTPUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 1. Kumpulkan sumber background / distractor
    bg_sources: List[np.ndarray] = []
    # Ambil distractor yang ada
    distractor_dir = PROJECT_ROOT / "dataset" / "yolo_dataset" / "images" / "train"
    if distractor_dir.exists():
        for f in distractor_dir.glob("distractor_hard_bg_*.jpg"):
            bg_img = cv2.imread(str(f))
            if bg_img is not None:
                bg_sources.append(bg_img)

    # Ambil frame dari laptop photo user sebagai background kuburan nyata
    laptop_p = Path("C:/Users/Lenovo/.gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/.user_uploaded/media_1794577750549_553aadb4.jpg")
    if laptop_p.exists():
        laptop_img = cv2.imread(str(laptop_p))
        if laptop_img is not None:
            # Crop viewport area kuburan
            crop_bg = laptop_img[100:800, 50:1100]
            bg_sources.append(crop_bg)

    # Jika bg kurang, buat synthetic dark graveyard canvas
    if not bg_sources:
        dummy_bg = np.zeros((720, 1280, 3), dtype=np.uint8)
        dummy_bg[:] = (35, 30, 25)
        bg_sources.append(dummy_bg)

    # 2. Kumpulkan Cutout per Kelas
    # --- KELAS 0: hidden_grounded (Idle, Walk, Hit) ---
    grounded_cutouts: List[np.ndarray] = []
    t_hidden = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"
    for name in [
        "template_idle_pre_leap_var1.png",
        "template_idle_pre_leap_var2.png",
        "template_hit_survivor_var1.png",
        "template_hit_wall_var1.png",
    ]:
        p = t_hidden / name
        if p.exists():
            c = cv2.imread(str(p))
            if c is not None:
                grounded_cutouts.append(c)

    # Tambahkan skin screenshots standing
    skin_dir = PROJECT_ROOT / "database" / "dataset" / "HIDDEN" / "PNG" / "SKIN"
    if skin_dir.exists():
        for sp in skin_dir.glob("*/*.png"):
            simg = cv2.imread(str(sp))
            if simg is not None:
                # crop killer center
                h, w = simg.shape[:2]
                cw = min(w, 400)
                cx = (w - cw) // 2
                grounded_cutouts.append(simg[:, cx:cx+cw])

    # --- KELAS 1: hidden_leap_airborne (Mid-Air) ---
    leap_cutouts: List[np.ndarray] = []
    for name in ["template_leap_airborne_var1.png", "template_leap_airborne_var2.png"]:
        p = t_hidden / name
        if p.exists():
            c = cv2.imread(str(p))
            if c is not None:
                leap_cutouts.append(c)

    # Tambahkan crop leap dari user upload
    user_dir = Path("C:/Users/Lenovo/.gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/.user_uploaded")
    for up_name in [
        "media_1794581792709_641305e9.png", # green leap
        "media_1794581792710_b9f458d2.png", # pink leap 1
        "media_1794581792712_2204fe7d.png", # pink leap 2
        "media_1794577878322_e9a6d7c6.png", # green leap 2
    ]:
        up_path = user_dir / up_name
        if up_path.exists():
            c = cv2.imread(str(up_path))
            if c is not None:
                leap_cutouts.append(c)

    # --- KELAS 2: hidden_mark_stab ---
    mark_cutouts: List[np.ndarray] = []
    for name in ["template_mark_solo_var1.png", "template_mark_solo_var2.png"]:
        p = t_hidden / name
        if p.exists():
            c = cv2.imread(str(p))
            if c is not None:
                mark_cutouts.append(c)

    # Referensi pose mark yang diekstrak sebelumnya
    ref_mark = Path("C:/Users/Lenovo/.gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/references/pose_case4_mark_stab_db.png")
    if ref_mark.exists():
        c = cv2.imread(str(ref_mark))
        if c is not None:
            mark_cutouts.append(c)

    print(f"Loaded cutouts: Grounded={len(grounded_cutouts)}, Leap={len(leap_cutouts)}, Mark={len(mark_cutouts)}")
    print(f"Loaded background sources: {len(bg_sources)}")

    def generate_single_sample(split: str, sample_idx: int) -> None:
        bg_raw = random.choice(bg_sources)
        # Resize background to target size (e.g. 640x360)
        target_w, target_h = img_size
        canvas = cv2.resize(bg_raw, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # 10% probabilitas menjadi Hard Distractor (tanpa killer sama sekali)
        if random.random() < 0.10:
            img_filename = f"sample_{split}_{sample_idx:04d}_distractor.jpg"
            lbl_filename = f"sample_{split}_{sample_idx:04d}_distractor.txt"
            cv2.imwrite(str(OUTPUT_DIR / "images" / split / img_filename), canvas)
            with open(OUTPUT_DIR / "labels" / split / lbl_filename, "w") as fp:
                pass # Empty file = negative sample
            return

        # Pilih kelas: 40% Leap (fokus utama), 35% Grounded, 25% Mark
        r_cls = random.random()
        if r_cls < 0.40:
            class_id = 1 # hidden_leap_airborne
            pool = leap_cutouts
        elif r_cls < 0.75:
            class_id = 0 # hidden_grounded
            pool = grounded_cutouts
        else:
            class_id = 2 # hidden_mark_stab
            pool = mark_cutouts

        if not pool:
            return

        cutout = random.choice(pool).copy()

        # Augmentasi 1: Green/Red Highlight Shader (50% probabilitas)
        if random.random() < 0.50:
            shader_color = (0, 255, 60) if random.random() < 0.80 else (0, 60, 255)
            cutout = apply_roblox_highlight(cutout, shader_color)

        # Augmentasi 2: Horizontal flip
        if random.random() < 0.50:
            cutout = cv2.flip(cutout, 1)

        # Augmentasi 3: Rescaling (ukuran killer di layar)
        ch, cw = cutout.shape[:2]
        # target killer height: 60px s/d 220px
        target_kh = random.randint(60, min(240, target_h - 20))
        scale = target_kh / float(ch)
        target_kw = max(15, int(cw * scale))
        cutout = cv2.resize(cutout, (target_kw, target_kh), interpolation=cv2.INTER_AREA)

        # Penempatan Spasial berdasarkan Kelas:
        target_kh = min(target_kh, target_h - 10)
        target_kw = min(target_kw, target_w - 10)
        cutout = cv2.resize(cutout, (target_kw, target_kh), interpolation=cv2.INTER_AREA)

        if class_id == 1:
            # LEAP: Karakter MELAYANG DI UDARA (Y atas s/d tengah layar)
            max_y = max(5, target_h - target_kh - 40)
            py = random.randint(5, max_y)
        else:
            # GROUNDED / MARK: Karakter MENAPAK TANAH (Y bawah layar)
            min_y = max(5, int((target_h - target_kh) * 0.40))
            max_y = max(min_y, target_h - target_kh - 5)
            py = random.randint(min_y, max_y)

        max_x = max(5, target_w - target_kw - 5)
        px = random.randint(5, max_x)

        # Pastikan batas aman
        py = max(0, min(target_h - target_kh, py))
        px = max(0, min(target_w - target_kw, px))

        # Seamless paste dengan alpha mask
        c_gray = cv2.cvtColor(cutout, cv2.COLOR_BGR2GRAY)
        _, c_mask = cv2.threshold(c_gray, 15, 255, cv2.THRESH_BINARY)
        roi = canvas[py:py+target_kh, px:px+target_kw]

        if roi.shape[:2] != cutout.shape[:2]:
            cutout = cv2.resize(cutout, (roi.shape[1], roi.shape[0]))
            c_mask = cv2.resize(c_mask, (roi.shape[1], roi.shape[0]))
            target_kw, target_kh = roi.shape[1], roi.shape[0]

        # Blend
        mask_inv = cv2.bitwise_not(c_mask)
        bg_part = cv2.bitwise_and(roi, roi, mask=mask_inv)
        fg_part = cv2.bitwise_and(cutout, cutout, mask=c_mask)
        canvas[py:py+target_kh, px:px+target_kw] = cv2.add(bg_part, fg_part)

        # Hitung koordinat YOLO (normalisasi 0.0 - 1.0)
        x_center = (px + target_kw / 2.0) / target_w
        y_center = (py + target_kh / 2.0) / target_h
        norm_w = target_kw / float(target_w)
        norm_h = target_kh / float(target_h)

        img_filename = f"sample_{split}_{sample_idx:04d}_cls{class_id}.jpg"
        lbl_filename = f"sample_{split}_{sample_idx:04d}_cls{class_id}.txt"

        cv2.imwrite(str(OUTPUT_DIR / "images" / split / img_filename), canvas)
        with open(OUTPUT_DIR / "labels" / split / lbl_filename, "w") as fp:
            fp.write(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}\n")

    print(f"Generating {num_train_samples} training samples...")
    for i in range(num_train_samples):
        generate_single_sample("train", i)

    print(f"Generating {num_val_samples} validation samples...")
    for i in range(num_val_samples):
        generate_single_sample("val", i)

    # Buat dataset.yaml
    dataset_yaml_path = OUTPUT_DIR / "dataset.yaml"
    yaml_content = f"""path: {OUTPUT_DIR.as_posix()}
train: images/train
val: images/val
nc: {len(CLASS_NAMES)}
names: {CLASS_NAMES}
"""
    with open(dataset_yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"Dataset successfully created at: {OUTPUT_DIR}")
    print(f"YAML config: {dataset_yaml_path}")
    return dataset_yaml_path


if __name__ == "__main__":
    build_multiclass_dataset(num_train_samples=400, num_val_samples=80)
