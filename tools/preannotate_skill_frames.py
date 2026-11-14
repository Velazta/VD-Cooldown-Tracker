"""Pre-Annotate Skill Frames Using Verified Multi-Template Matching.

Violence District Cooldown Tracker — Rebuild Phase 2/3 Tool
Uses verified cutouts of The Hidden (Leap airborne & Mark across skins) and Survivor
to propose initial candidate bounding boxes on frames inside known skill windows.
Negative / background frames remain completely empty (0 boxes).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


def match_best_template(
    image: np.ndarray,
    templates: List[Tuple[int, np.ndarray]],  # list of (class_id, tpl_img)
    threshold: float = 0.45,
) -> List[Tuple[int, float, float, float, float]]:
    """Runs multi-scale template matching and returns non-overlapping YOLO boxes."""
    boxes: List[Tuple[int, float, float, float, float]] = []
    ih, iw = image.shape[:2]

    for cid, tpl in templates:
        th, tw = tpl.shape[:2]
        if th >= ih or tw >= iw:
            continue

        # Try a few scales: 0.7x, 1.0x, 1.3x
        for scale in [0.8, 1.0, 1.2]:
            scaled_w = int(round(tw * scale))
            scaled_h = int(round(th * scale))
            if scaled_w >= iw or scaled_h >= ih or scaled_w < 10 or scaled_h < 10:
                continue

            scaled_tpl = cv2.resize(tpl, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(image, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)

            if max_v >= threshold:
                x1, y1 = max_l
                x2, y2 = x1 + scaled_w, y1 + scaled_h
                xc_norm = (x1 + scaled_w / 2.0) / iw
                yc_norm = (y1 + scaled_h / 2.0) / ih
                w_norm = scaled_w / iw
                h_norm = scaled_h / ih
                boxes.append((cid, xc_norm, yc_norm, w_norm, h_norm))
                break  # match found for this template

    return boxes


def run_preannotation(
    dataset_dir: Path = Path("dataset/yolo"),
    metadata_path: Path = Path("dataset/yolo/metadata.json"),
    threshold: float = 0.42,
) -> None:
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Collect killer templates
    k_cutouts = [
        Path("dataset/killer_cutouts/crop_hidden_leap2_0.jpg"),
        Path("dataset/killer_cutouts/crop_hidden_leap3_0.jpg"),
        Path("dataset/killer_cutouts/crop_hidden_mark5_1.jpg"),
        Path("dataset/killer_cutouts/crop_hidden_mark6_1.jpg"),
        Path("docs/references/hidden_leap_airborne_peach1.png"),
        Path("docs/references/hidden_leap_airborne_green_fedora.png"),
    ]
    # Collect survivor templates
    s_cutouts = [
        Path("dataset/survivor_cutouts/survivor_white_shirt_leap4.png"),
        Path("dataset/survivor_cutouts/survivor_user_laptop_1.png"),
    ]

    templates: List[Tuple[int, np.ndarray]] = []
    for kp in k_cutouts:
        if kp.exists():
            im = cv2.imread(str(kp))
            if im is not None:
                templates.append((0, im))

    for sp in s_cutouts:
        if sp.exists():
            im = cv2.imread(str(sp))
            if im is not None:
                templates.append((1, im))

    print(f"Loaded {len(templates)} verified reference templates.")

    annotated_count = 0
    for frame_info in meta.get("frames", []):
        # Only annotate frames that are in known skill windows
        if not frame_info.get("in_skill_window", False):
            continue

        split = frame_info["split"]
        img_rel = frame_info["image_relpath"]
        lbl_rel = frame_info["label_relpath"]

        img_path = dataset_dir / img_rel
        lbl_path = dataset_dir / lbl_rel

        if not img_path.exists():
            continue

        # If already has non-empty label, keep it
        if lbl_path.exists() and lbl_path.stat().st_size > 0:
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        boxes = match_best_template(img, templates, threshold=threshold)
        if boxes:
            lines = [f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}" for cid, xc, yc, w, h in boxes]
            lbl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            annotated_count += 1
            print(f"  [{split.upper()}] Pre-annotated {img_path.name} with {len(boxes)} box(es)")

    print(f"\nDone! Pre-annotated {annotated_count} skill-window frames.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-annotate skill frames with verified templates.")
    parser.add_argument("--dataset", default="dataset/yolo", help="YOLO dataset path")
    parser.add_argument("--metadata", default="dataset/yolo/metadata.json", help="Path to metadata.json")
    parser.add_argument("--threshold", type=float, default=0.42, help="Normalized correlation threshold")

    args = parser.parse_args()
    run_preannotation(dataset_dir=Path(args.dataset), metadata_path=Path(args.metadata), threshold=args.threshold)


if __name__ == "__main__":
    main()
