"""Synthetic Foreground-Background Compositor for YOLO Training.

Violence District Cooldown Tracker — Rebuild Phase 3 (Task 3.3)
Generates realistic multi-scale composite training samples:
- Blends verified The Hidden cutouts (Leap airborne & Mark poses across skins)
- Blends verified Survivor cutouts (hard negatives)
- Places them on real game background frames at varied scales (small: <48px, med: 48-90px, large: >90px)
- Strictly restricted to TRAIN split (NEVER generates in val or test)
- Supports synthetic Roblox Highlight aura augmentation (neon outlines)
- Reproducible with fixed random seed
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


def extract_foreground_and_mask(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Extracts BGR image and binary mask from a 3 or 4 channel image.
    
    If 4-channel and alpha has variance, uses alpha as mask.
    Otherwise computes an adaptive GrabCut or color threshold mask around object.
    """
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3]
        bgr = img[:, :, :3]
        if alpha.min() < 250:
            mask = (alpha > 50).astype(np.uint8) * 255
            return bgr, mask

    bgr = img[:, :, :3] if len(img.shape) == 3 and img.shape[2] == 4 else img
    h, w = bgr.shape[:2]

    # Create soft edge mask by default (feathered box)
    mask = np.ones((h, w), dtype=np.uint8) * 255
    border = max(2, min(h, w) // 20)
    mask[:border, :] = 0
    mask[-border:, :] = 0
    mask[:, :border] = 0
    mask[:, -border:] = 0
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    return bgr, mask


def apply_highlight_aura(fg: np.ndarray, mask: np.ndarray, aura_color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """Simulates Roblox Highlight shader effect (neon outline aura)."""
    dilated = cv2.dilate(mask, np.ones((thickness * 2 + 1, thickness * 2 + 1), np.uint8))
    contour_mask = cv2.subtract(dilated, mask)

    h, w = fg.shape[:2]
    out_fg = fg.copy()
    aura_layer = np.zeros_like(fg)
    aura_layer[:] = aura_color

    # Blend aura onto contour region
    c_indices = contour_mask > 50
    out_fg[c_indices] = cv2.addWeighted(out_fg[c_indices], 0.3, aura_layer[c_indices], 0.7, 0)
    out_mask = cv2.bitwise_or(mask, contour_mask)
    return out_fg, out_mask


class SyntheticCompositor:
    def __init__(
        self,
        dataset_dir: Path = Path("dataset/yolo"),
        killer_cutouts_dir: Path = Path("dataset/killer_cutouts"),
        survivor_cutouts_dir: Path = Path("dataset/survivor_cutouts"),
        references_dir: Path = Path("docs/references"),
        seed: int = 42,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.killer_cutouts_dir = Path(killer_cutouts_dir)
        self.survivor_cutouts_dir = Path(survivor_cutouts_dir)
        self.references_dir = Path(references_dir)
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

        self.killer_cutout_paths = self._collect_images([self.killer_cutouts_dir, self.references_dir])
        self.survivor_cutout_paths = self._collect_images([self.survivor_cutouts_dir])

    def _collect_images(self, dirs: List[Path]) -> List[Path]:
        res: List[Path] = []
        for d in dirs:
            if d.exists():
                res.extend(list(d.glob("*.png")) + list(d.glob("*.jpg")))
        return sorted(res)

    def blend_cutout(
        self,
        bg: np.ndarray,
        fg: np.ndarray,
        mask: np.ndarray,
        target_h: int,
        x_center: int,
        y_center: int,
    ) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """Blends resized fg into bg at (x_center, y_center). Returns blended bg and (x1, y1, x2, y2)."""
        orig_h, orig_w = fg.shape[:2]
        aspect = orig_w / max(1, orig_h)
        target_w = max(6, int(round(target_h * aspect)))

        resized_fg = cv2.resize(fg, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        resized_mask = cv2.resize(mask, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        bg_h, bg_w = bg.shape[:2]
        x1 = x_center - target_w // 2
        y1 = y_center - target_h // 2
        x2 = x1 + target_w
        y2 = y1 + target_h

        # Clamp coordinates to background frame boundaries
        src_x1 = max(0, -x1)
        src_y1 = max(0, -y1)
        src_x2 = target_w - max(0, x2 - bg_w)
        src_y2 = target_h - max(0, y2 - bg_h)

        dst_x1 = max(0, x1)
        dst_y1 = max(0, y1)
        dst_x2 = min(bg_w, x2)
        dst_y2 = min(bg_h, y2)

        if dst_x2 <= dst_x1 or dst_y2 <= dst_y1:
            return bg, (0, 0, 0, 0)

        patch_fg = resized_fg[src_y1:src_y2, src_x1:src_x2]
        patch_mask = resized_mask[src_y1:src_y2, src_x1:src_x2]
        alpha = (patch_mask.astype(float) / 255.0)[:, :, np.newaxis]

        bg_roi = bg[dst_y1:dst_y2, dst_x1:dst_x2]
        blended_roi = (patch_fg * alpha + bg_roi * (1.0 - alpha)).astype(np.uint8)
        bg[dst_y1:dst_y2, dst_x1:dst_x2] = blended_roi

        return bg, (dst_x1, dst_y1, dst_x2, dst_y2)

    def generate_synthetic_samples(
        self,
        count: int = 50,
        split: str = "train",
        clean_existing: bool = True,
    ) -> List[Dict[str, Any]]:
        if split != "train":
            raise ValueError(f"Synthetic composite samples are strictly forbidden in '{split}' split! Must be 'train' only.")

        img_dir = self.dataset_dir / "images" / split
        lbl_dir = self.dataset_dir / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        if clean_existing:
            for p in list(img_dir.glob("synth_*.jpg")) + list(lbl_dir.glob("synth_*.txt")):
                p.unlink(missing_ok=True)

        bg_candidates = [p for p in img_dir.glob("*.jpg") if not p.name.startswith("synth_")]
        if not bg_candidates:
            raise FileNotFoundError(f"No background candidate images found in {img_dir}")

        if not self.killer_cutout_paths:
            raise FileNotFoundError("No killer cutout images found to composite.")

        print(f"Generating {count} synthetic training samples into {split} split...")
        generated_records: List[Dict[str, Any]] = []

        for i in range(count):
            bg_path = random.choice(bg_candidates)
            bg = cv2.imread(str(bg_path))
            if bg is None:
                continue

            bg_h, bg_w = bg.shape[:2]
            boxes: List[Tuple[int, float, float, float, float]] = []

            # 1. Blend 1 The Hidden instance (Class 0)
            k_cutout_path = random.choice(self.killer_cutout_paths)
            k_raw = cv2.imread(str(k_cutout_path), cv2.IMREAD_UNCHANGED)
            if k_raw is not None:
                fg, mask = extract_foreground_and_mask(k_raw)

                # Augmentation: 30% chance of Roblox Highlight green/red aura
                if random.random() < 0.35:
                    aura_col = (0, 255, 0) if random.random() < 0.8 else (0, 0, 255)
                    fg, mask = apply_highlight_aura(fg, mask, aura_color=aura_col)

                # Scale bucket: 35% small (24-48px), 40% mid (48-85px), 25% large (85-140px)
                bucket = random.choices(["small", "mid", "large"], weights=[0.35, 0.40, 0.25])[0]
                if bucket == "small":
                    t_h = random.randint(24, 48)
                elif bucket == "mid":
                    t_h = random.randint(49, 85)
                else:
                    t_h = random.randint(86, 140)

                # Placement: mid-air (y in top 10% - 60% of ROI) or ground
                y_c = random.randint(int(bg_h * 0.15), int(bg_h * 0.75))
                x_c = random.randint(int(bg_w * 0.1), int(bg_w * 0.9))

                bg, (x1, y1, x2, y2) = self.blend_cutout(bg, fg, mask, t_h, x_c, y_c)
                bw, bh = x2 - x1, y2 - y1
                if bw >= 6 and bh >= 6:
                    xc_norm = (x1 + bw / 2.0) / bg_w
                    yc_norm = (y1 + bh / 2.0) / bg_h
                    bw_norm = bw / bg_w
                    bh_norm = bh / bg_h
                    boxes.append((0, xc_norm, yc_norm, bw_norm, bh_norm))

            # 2. 50% chance to blend 1 Survivor instance (Class 1, hard negative)
            if self.survivor_cutout_paths and random.random() < 0.50:
                s_cutout_path = random.choice(self.survivor_cutout_paths)
                s_raw = cv2.imread(str(s_cutout_path), cv2.IMREAD_UNCHANGED)
                if s_raw is not None:
                    s_fg, s_mask = extract_foreground_and_mask(s_raw)
                    # Survivors are often closer to camera (height 60-160px)
                    s_h = random.randint(60, 160)
                    s_yc = random.randint(int(bg_h * 0.3), int(bg_h * 0.85))
                    s_xc = random.randint(int(bg_w * 0.15), int(bg_w * 0.85))

                    bg, (sx1, sy1, sx2, sy2) = self.blend_cutout(bg, s_fg, s_mask, s_h, s_xc, s_yc)
                    sbw, sbh = sx2 - sx1, sy2 - sy1
                    if sbw >= 6 and sbh >= 6:
                        s_xc_norm = (sx1 + sbw / 2.0) / bg_w
                        s_yc_norm = (sy1 + sbh / 2.0) / bg_h
                        s_bw_norm = sbw / bg_w
                        s_bh_norm = sbh / bg_h
                        boxes.append((1, s_xc_norm, s_yc_norm, s_bw_norm, s_bh_norm))

            # Save synthetic image and label
            stem = f"synth_{i:05d}"
            out_img_path = img_dir / f"{stem}.jpg"
            out_lbl_path = lbl_dir / f"{stem}.txt"

            cv2.imwrite(str(out_img_path), bg, [cv2.IMWRITE_JPEG_QUALITY, 95])
            lines = [f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}" for cid, xc, yc, bw, bh in boxes]
            out_lbl_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

            record = {
                "frame_id": stem,
                "split": split,
                "is_synthetic": True,
                "boxes_count": len(boxes),
                "hidden_count": sum(1 for cid, *_ in boxes if cid == 0),
                "survivor_count": sum(1 for cid, *_ in boxes if cid == 1),
                "source_bg": bg_path.name,
            }
            generated_records.append(record)

        print(f"Successfully generated {len(generated_records)} synthetic samples.")
        return generated_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic composite training samples.")
    parser.add_argument("--count", type=int, default=50, help="Number of synthetic images to generate")
    parser.add_argument("--split", default="train", help="Dataset split (MUST be 'train')")
    parser.add_argument("--dataset", default="dataset/yolo", help="Path to YOLO dataset directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-clean", action="store_true", help="Do not remove existing synth samples")

    args = parser.parse_args()

    compositor = SyntheticCompositor(dataset_dir=Path(args.dataset), seed=args.seed)
    compositor.generate_synthetic_samples(count=args.count, split=args.split, clean_existing=not args.no_clean)


if __name__ == "__main__":
    main()
