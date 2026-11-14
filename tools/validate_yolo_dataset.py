"""YOLO Dataset Integrity Validator & data.yaml Generator.

Violence District Cooldown Tracker — Rebuild Phase 2 (Task 2.3)
Validates:
1. Every image in dataset/yolo/images/{split} has matching label in dataset/yolo/labels/{split}
2. Classes are strictly 0 (hidden) or 1 (survivor)
3. Normalized coordinates in [0.0, 1.0]
4. Positive dimensions (width > 0, height > 0)
5. No extreme duplicate boxes (IoU > 0.95 within same image)
6. Zero video leakage across train/val/test splits
7. Automatically writes/updates training/data.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def calculate_box_iou(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
    """Calculates IoU between two YOLO format boxes (xc, yc, w, h)."""
    xc1, yc1, w1, h1 = b1
    xc2, yc2, w2, h2 = b2

    x1_min, y1_min = xc1 - w1 / 2.0, yc1 - h1 / 2.0
    x1_max, y1_max = xc1 + w1 / 2.0, yc1 + h1 / 2.0

    x2_min, y2_min = xc2 - w2 / 2.0, yc2 - h2 / 2.0
    x2_max, y2_max = xc2 + w2 / 2.0, yc2 + h2 / 2.0

    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)

    inter_w = max(0.0, inter_xmax - inter_xmin)
    inter_h = max(0.0, inter_ymax - inter_ymin)
    inter_area = inter_w * inter_h

    area1 = w1 * h1
    area2 = w2 * h2
    union_area = area1 + area2 - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def validate_yolo_dataset(
    dataset_dir: Path = Path("dataset/yolo"),
    classes_file: Path = Path("training/classes.yaml"),
    splits_file: Optional[Path] = Path("dataset/splits.json"),
    data_yaml_out: Optional[Path] = Path("training/data.yaml"),
) -> Tuple[bool, List[str], Dict[str, Any]]:
    errors: List[str] = []
    stats: Dict[str, Any] = {
        "splits": {},
        "total_images": 0,
        "total_labels": 0,
        "class_counts": {0: 0, 1: 0},
        "background_images": 0,
    }

    if not dataset_dir.exists():
        errors.append(f"Dataset directory not found: {dataset_dir}")
        return False, errors, stats

    images_root = dataset_dir / "images"
    labels_root = dataset_dir / "labels"

    if not images_root.exists() or not labels_root.exists():
        errors.append("Dataset must contain both 'images' and 'labels' directories.")
        return False, errors, stats

    split_videos: Dict[str, Set[str]] = {"train": set(), "val": set(), "test": set()}

    for split in ["train", "val", "test"]:
        img_split_dir = images_root / split
        lbl_split_dir = labels_root / split

        if not img_split_dir.exists():
            continue

        images = sorted(list(img_split_dir.glob("*.jpg")) + list(img_split_dir.glob("*.png")))
        split_stats = {"images": len(images), "boxes": 0, "hidden": 0, "survivor": 0, "background": 0}

        for img_path in images:
            stats["total_images"] += 1
            # Infer video stem (everything before _f\d+)
            parts = img_path.stem.split("_f")
            if len(parts) >= 2:
                vid_stem = parts[0]
                split_videos[split].add(vid_stem)

            # Match label file
            lbl_path = lbl_split_dir / f"{img_path.stem}.txt"
            if not lbl_path.exists():
                errors.append(f"Missing label file for image: {img_path}")
                continue

            content = lbl_path.read_text(encoding="utf-8").strip()
            if not content:
                # Valid empty background frame
                split_stats["background"] += 1
                stats["background_images"] += 1
                continue

            lines = content.splitlines()
            boxes_in_frame: List[Tuple[float, float, float, float]] = []

            for line_no, line in enumerate(lines, 1):
                tokens = line.strip().split()
                if len(tokens) != 5:
                    errors.append(f"{lbl_path}:{line_no} Invalid YOLO format (expected 5 tokens, got {len(tokens)})")
                    continue

                try:
                    cls_id = int(tokens[0])
                    xc, yc, w, h = map(float, tokens[1:])
                except ValueError:
                    errors.append(f"{lbl_path}:{line_no} Non-numeric values in label line: {line}")
                    continue

                if cls_id not in (0, 1):
                    errors.append(f"{lbl_path}:{line_no} Invalid class ID {cls_id} (allowed: 0=hidden, 1=survivor)")
                    continue

                for val, name in [(xc, "xc"), (yc, "yc"), (w, "w"), (h, "h")]:
                    if not (0.0 <= val <= 1.0):
                        errors.append(f"{lbl_path}:{line_no} Coordinate {name}={val} out of bounds [0.0, 1.0]")

                if w <= 0.0 or h <= 0.0:
                    errors.append(f"{lbl_path}:{line_no} Non-positive box dimensions w={w}, h={h}")

                curr_box = (xc, yc, w, h)
                for existing_box in boxes_in_frame:
                    if calculate_box_iou(curr_box, existing_box) > 0.95:
                        errors.append(f"{lbl_path}:{line_no} Duplicate bounding box with IoU > 0.95: {line}")
                boxes_in_frame.append(curr_box)

                split_stats["boxes"] += 1
                stats["total_labels"] += 1
                if cls_id == 0:
                    split_stats["hidden"] += 1
                    stats["class_counts"][0] += 1
                else:
                    split_stats["survivor"] += 1
                    stats["class_counts"][1] += 1

        stats["splits"][split] = split_stats

    # Check video split isolation (zero leakage)
    train_vids = split_videos.get("train", set())
    val_vids = split_videos.get("val", set())
    test_vids = split_videos.get("test", set())

    leak_train_val = train_vids.intersection(val_vids)
    leak_train_test = train_vids.intersection(test_vids)
    leak_val_test = val_vids.intersection(test_vids)

    if leak_train_val:
        errors.append(f"Video leakage detected between train and val: {leak_train_val}")
    if leak_train_test:
        errors.append(f"Video leakage detected between train and test: {leak_train_test}")
    if leak_val_test:
        errors.append(f"Video leakage detected between val and test: {leak_val_test}")

    # Generate training/data.yaml if requested and no fatal structure errors
    if data_yaml_out and not errors:
        data_yaml_out.parent.mkdir(parents=True, exist_ok=True)
        abs_dataset = dataset_dir.resolve()
        yaml_lines = [
            f"# Auto-generated by tools/validate_yolo_dataset.py",
            f"path: {abs_dataset.as_posix()}",
            f"train: images/train",
            f"val: images/val",
            f"test: images/test",
            f"",
            f"nc: 2",
            f"names:",
            f"  0: hidden",
            f"  1: survivor",
            f"",
        ]
        data_yaml_out.write_text("\n".join(yaml_lines), encoding="utf-8")
        print(f"Generated data.yaml at {data_yaml_out}")

    is_valid = len(errors) == 0
    return is_valid, errors, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate YOLO dataset format and integrity.")
    parser.add_argument("--dataset", default="dataset/yolo", help="Path to YOLO dataset directory")
    parser.add_argument("--classes", default="training/classes.yaml", help="Path to classes.yaml")
    parser.add_argument("--data-yaml", default="training/data.yaml", help="Output path for data.yaml")

    args = parser.parse_args()

    is_valid, errors, stats = validate_yolo_dataset(
        dataset_dir=Path(args.dataset),
        classes_file=Path(args.classes),
        data_yaml_out=Path(args.data_yaml),
    )

    print("=" * 60)
    print("YOLO DATASET VALIDATION REPORT")
    print("=" * 60)
    print(f"Total Images: {stats['total_images']}")
    print(f"Total Boxes:  {stats['total_labels']}")
    print(f"  - Hidden (0):   {stats['class_counts'][0]}")
    print(f"  - Survivor (1): {stats['class_counts'][1]}")
    print(f"  - Background:   {stats['background_images']}")
    print("-" * 60)
    for sp, s in stats["splits"].items():
        print(f"[{sp.upper()}] Images: {s['images']} | Boxes: {s['boxes']} (Hidden: {s['hidden']}, Survivor: {s['survivor']}, Bg: {s['background']})")
    print("=" * 60)

    if not is_valid:
        print(f"\nVALIDATION FAILED with {len(errors)} error(s):")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors.")
        sys.exit(1)
    else:
        print("\nSUCCESS: Dataset is 100% schema-valid with ZERO leakage!")


if __name__ == "__main__":
    main()
