"""YOLO Dataset Annotator, Synthetic Augmenter & Splitter.

Violence District Cooldown Tracker — Week 5 (Day 26)
Converts spatial annotations to standardized YOLO format (.txt),
generates realistic synthetic augmentations (scale, rotation, lighting, flips),
adds negative hard distractors (empty labels for rocks/pillars),
and splits into balanced Train (80%) / Val (20%) sets.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class AnnotationSample:
    """Sampel data citra dengan label YOLO."""
    image_path: Path
    boxes: List[Tuple[int, float, float, float, float]]  # (class_id, x_center, y_center, w, h)
    phase: str
    is_augmented: bool = False


@dataclass
class DatasetSplitSummary:
    """Ringkasan statistik dataset YOLO yang dihasilkan."""
    total_images: int
    train_count: int
    val_count: int
    augmented_count: int
    negative_distractor_count: int
    class_names: List[str]
    split_ratio: str
    output_dir: str


class DatasetAnnotator:
    """Generator dataset terstandarisasi YOLOv8 dengan augmentasi sintetis & hard distractors."""

    def __init__(
        self,
        annotations_json: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        train_ratio: float = 0.80,
        random_seed: int = 42,
    ) -> None:
        import warnings
        if annotations_json is not None:
            self.annotations_json = Path(annotations_json).resolve()
        else:
            legacy_p = PROJECT_ROOT / "dataset" / "legacy_mog2" / "bounding_boxes.json"
            if legacy_p.exists():
                warnings.warn(
                    "DatasetAnnotator reading legacy MOG2 bounding boxes! Coarse draft proposal only.",
                    UserWarning,
                    stacklevel=2,
                )
                self.annotations_json = legacy_p
            else:
                self.annotations_json = PROJECT_ROOT / "dataset" / "annotations" / "bounding_boxes.json"
        self.output_dir = output_dir or (PROJECT_ROOT / "dataset" / "yolo_dataset")
        self.train_ratio = train_ratio
        self.random_seed = random_seed
        random.seed(random_seed)
        np.random.seed(random_seed)

    def load_base_annotations(self) -> List[AnnotationSample]:
        """Memuat anotasi valid dari bounding_boxes.json."""
        if not self.annotations_json.exists():
            return []

        with open(self.annotations_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples: List[AnnotationSample] = []
        base_dir = PROJECT_ROOT / "dataset"

        for item in data.get("annotations", []):
            if not item.get("has_detection", False) or not item.get("bbox"):
                continue

            rel_img = item.get("relative_image_path", "")
            img_path = base_dir / rel_img
            if not img_path.exists():
                continue

            bb = item["bbox"]
            xc = float(bb["x_center_norm"])
            yc = float(bb["y_center_norm"])
            wn = float(bb["width_norm"])
            hn = float(bb["height_norm"])

            # Class 0: killer_the_hidden
            boxes = [(0, xc, yc, wn, hn)]
            samples.append(
                AnnotationSample(
                    image_path=img_path,
                    boxes=boxes,
                    phase=item.get("phase", "general"),
                    is_augmented=False,
                )
            )

        return samples

    def augment_sample(
        self,
        image: np.ndarray,
        box: Tuple[int, float, float, float, float],
        aug_type: str,
    ) -> Tuple[np.ndarray, Tuple[int, float, float, float, float]]:
        """Menerapkan transformasi augmentasi citra dan koordinat bounding box."""
        cid, xc, yc, wn, hn = box
        h, w = image.shape[:2]

        if aug_type == "hflip":
            aug_img = cv2.flip(image, 1)
            new_box = (cid, 1.0 - xc, yc, wn, hn)
            return aug_img, new_box

        elif aug_type == "darker":
            # Reduksi gamma untuk mensimulasikan kegelapan map kuburan
            gamma = 0.70
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            aug_img = cv2.LUT(image, table)
            return aug_img, box

        elif aug_type == "brighter":
            # Peningkatan gamma untuk mensimulasikan pantulan senter survivor
            gamma = 1.35
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            aug_img = cv2.LUT(image, table)
            return aug_img, box

        elif aug_type == "rotate":
            # Rotasi ringan +- 8 derajat (kemiringan sudut kamera)
            angle = random.choice([-8.0, 8.0])
            center = (w / 2.0, h / 2.0)
            rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
            aug_img = cv2.warpAffine(image, rot_mat, (w, h), borderMode=cv2.BORDER_REFLECT)
            # Koordinat bbox tetap stabil untuk rotasi kecil
            return aug_img, box

        return image, box

    def find_hard_distractors(self) -> List[Path]:
        """Mencari sampel gambar negatif (batu, pilar, dinding tanpa killer)."""
        distractors: List[Path] = []
        # Ambil dari snapshot dataset jika ada
        dataset_dir = PROJECT_ROOT / "dataset"
        for p in dataset_dir.glob("snapshot_*.png"):
            if p.exists() and p.stat().st_size > 100000:
                distractors.append(p)
        return distractors[:15]  # Ambil hingga 15 sampel background negatif

    def build_dataset(
        self,
        target_train_count: int = 120,
        target_val_count: int = 30,
    ) -> DatasetSplitSummary:
        """Membangun dataset YOLO lengkap dengan gambar dan berkas teks label."""
        base_samples = self.load_base_annotations()
        if not base_samples:
            raise RuntimeError(f"Tidak ada anotasi yang ditemukan di {self.annotations_json}")

        random.shuffle(base_samples)

        # Siapkan direktori output YOLO
        train_img_dir = self.output_dir / "images" / "train"
        val_img_dir = self.output_dir / "images" / "val"
        train_lbl_dir = self.output_dir / "labels" / "train"
        val_lbl_dir = self.output_dir / "labels" / "val"

        for d in (train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

        # Tentukan split Train vs Val
        split_idx = int(len(base_samples) * self.train_ratio)
        train_base = base_samples[:split_idx]
        val_base = base_samples[split_idx:]

        augmented_counter = 0

        # Helper penyimpanan sampel
        def save_sample(sample_img: np.ndarray, boxes: List[Tuple[int, float, float, float, float]], base_name: str, is_train: bool) -> None:
            img_dir = train_img_dir if is_train else val_img_dir
            lbl_dir = train_lbl_dir if is_train else val_lbl_dir

            img_file = img_dir / f"{base_name}.jpg"
            lbl_file = lbl_dir / f"{base_name}.txt"

            # Simpan citra JPEG kualitas tinggi
            cv2.imwrite(str(img_file), sample_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Simpan label YOLO (.txt format: class xc yc w h)
            with open(lbl_file, "w", encoding="utf-8") as lf:
                for b in boxes:
                    cid, xc, yc, bw, bh = b
                    lf.write(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")

        # 1. Tulis sampel Train asli + augmentasi
        for idx, s in enumerate(train_base):
            img = cv2.imread(str(s.image_path))
            if img is None:
                continue
            name_base = f"the_hidden_train_{idx:04d}"
            save_sample(img, s.boxes, name_base, is_train=True)

            # Buat 2 variasi augmentasi untuk memperkaya variasi
            for aug_name in ("hflip", "darker"):
                aug_img, aug_box = self.augment_sample(img, s.boxes[0], aug_name)
                aug_name_base = f"the_hidden_train_{idx:04d}_aug_{aug_name}"
                save_sample(aug_img, [aug_box], aug_name_base, is_train=True)
                augmented_counter += 1

        # 2. Tulis sampel Validation asli + variasi
        for idx, s in enumerate(val_base):
            img = cv2.imread(str(s.image_path))
            if img is None:
                continue
            name_base = f"the_hidden_val_{idx:04d}"
            save_sample(img, s.boxes, name_base, is_train=False)

        # 3. Tulis Negative Hard Distractors (Gambar background tanpa box)
        distractors = self.find_hard_distractors()
        for idx, dp in enumerate(distractors):
            dimg = cv2.imread(str(dp))
            if dimg is not None:
                is_train_dist = (idx % 4 != 0)  # 75% train, 25% val
                dist_name = f"distractor_hard_bg_{idx:03d}"
                # Kotak kosong [] -> file label kosong
                save_sample(dimg, [], dist_name, is_train=is_train_dist)

        # 4. Tulis dataset.yaml untuk YOLOv8 / Ultralytics
        yaml_content = f"""path: {self.output_dir.resolve().as_posix()}
train: images/train
val: images/val
nc: 1
names: ['killer_the_hidden']
"""
        with open(self.output_dir / "dataset.yaml", "w", encoding="utf-8") as yf:
            yf.write(yaml_content)

        # Hitung total file yang dihasilkan
        total_train = len(list(train_img_dir.glob("*.jpg")))
        total_val = len(list(val_img_dir.glob("*.jpg")))
        total_imgs = total_train + total_val

        summary = DatasetSplitSummary(
            total_images=total_imgs,
            train_count=total_train,
            val_count=total_val,
            augmented_count=augmented_counter,
            negative_distractor_count=len(distractors),
            class_names=["killer_the_hidden"],
            split_ratio=f"{int(self.train_ratio*100)}/{int((1-self.train_ratio)*100)}",
            output_dir=str(self.output_dir),
        )

        with open(self.output_dir / "dataset_summary.json", "w", encoding="utf-8") as sf:
            json.dump(asdict(summary), sf, indent=2)

        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO Dataset Annotator & Augmentation Engine")
    parser.add_argument("--ratio", type=float, default=0.80, help="Train ratio (default 0.80)")
    args = parser.parse_args()

    annotator = DatasetAnnotator(train_ratio=args.ratio)
    print("Membangun dataset YOLO terstandarisasi dengan augmentasi sintetis...")
    res = annotator.build_dataset()

    print(f"Selesai! Total gambar dataset: {res.total_images}")
    print(f"Train split: {res.train_count} citra | Val split: {res.val_count} citra")
    print(f"Sampel teraugmentasi: {res.augmented_count} | Hard Distractors: {res.negative_distractor_count}")
    print(f"Direktori output: {res.output_dir}")
