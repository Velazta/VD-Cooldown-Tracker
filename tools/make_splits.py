"""Leak-Free Video-Level Dataset Splitter.

Violence District Cooldown Tracker — Detector Rebuild (Phase 1)
Partitions gameplay video files into strictly disjoint Train, Validation, and Test sets:
- Video-level partitioning (ZERO frame leakage between splits).
- Ensures balanced distribution of skill types (Leap, Mark, Negative).
- Reserves unseen skin variations specifically for the Test set.
- Exports mapping to dataset/splits.json.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPLITS_PATH = PROJECT_ROOT / "dataset" / "splits.json"


def verify_no_leakage(splits: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
    """Memverifikasi bahwa tidak ada video yang muncul di lebih dari satu split.
    
    Returns:
        (is_leak_free, list_of_leakage_errors)
    """
    errors: List[str] = []
    seen_videos: Dict[str, str] = {}

    for split_name, video_list in splits.items():
        for v in video_list:
            if v in seen_videos:
                errors.append(f"LEAKAGE DETECTED: Video '{v}' appears in both '{seen_videos[v]}' and '{split_name}'!")
            else:
                seen_videos[v] = split_name

    return (len(errors) == 0), errors


def create_video_splits(
    videos_metadata: List[Dict[str, Any]],
    test_skin_prefixes: Optional[List[str]] = None,
    val_ratio: float = 0.20,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Membagi daftar video ke dalam train, val, test secara deterministik dan seimbang."""
    rng = random.Random(random_seed)
    test_prefixes = test_skin_prefixes or ["hidden3_"]

    train_videos: List[str] = []
    val_videos: List[str] = []
    test_videos: List[str] = []

    # Kelompokkan video berdasarkan tipe skill agar representasi seimbang
    categories: Dict[str, List[str]] = {
        "leap": [],
        "mark": [],
        "negative": []
    }

    for vm in videos_metadata:
        vname = vm.get("file_name") or vm.get("video_name") or ""
        cat = vm.get("category", "")
        is_leap = vm.get("is_positive_leap", False)

        # 1. Jika video cocok dengan unseen skin prefix, langsung masukkan ke TEST
        if any(vname.startswith(p) for p in test_prefixes):
            test_videos.append(vname)
            continue

        if is_leap or "leap" in cat or "leap" in vname:
            categories["leap"].append(vname)
        elif "mark" in cat or "mark" in vname:
            categories["mark"].append(vname)
        else:
            categories["negative"].append(vname)

    # Bagi sisa video per kategori ke train, val, dan test
    for cname, vlist in categories.items():
        rng.shuffle(vlist)
        n = len(vlist)
        if n == 0:
            continue
        elif n == 1:
            train_videos.append(vlist[0])
        elif n == 2:
            train_videos.append(vlist[0])
            val_videos.append(vlist[1])
        else:
            n_val = max(1, int(round(n * val_ratio)))
            n_test = max(1, int(round(n * 0.15)))
            
            v_val = vlist[:n_val]
            v_test = vlist[n_val:n_val + n_test]
            v_train = vlist[n_val + n_test:]
            
            val_videos.extend(v_val)
            test_videos.extend(v_test)
            train_videos.extend(v_train)

    # Buat reverse lookup mapping
    video_to_split: Dict[str, str] = {}
    for v in train_videos:
        video_to_split[v] = "train"
    for v in val_videos:
        video_to_split[v] = "val"
    for v in test_videos:
        video_to_split[v] = "test"

    splits_data = {
        "schema_version": 1,
        "split_strategy": "by_video_leak_free",
        "total_videos": len(video_to_split),
        "unseen_test_skin_prefixes": test_prefixes,
        "counts": {
            "train": len(train_videos),
            "val": len(val_videos),
            "test": len(test_videos),
        },
        "splits": {
            "train": sorted(train_videos),
            "val": sorted(val_videos),
            "test": sorted(test_videos),
        },
        "video_to_split": video_to_split,
    }

    is_clean, leak_errs = verify_no_leakage(splits_data["splits"])
    if not is_clean:
        raise ValueError(f"Split generation failed leakage check: {leak_errs}")

    return splits_data


def generate_and_save_splits(
    catalog_path: Path = PROJECT_ROOT / "dataset" / "catalog.json",
    output_path: Path = DEFAULT_SPLITS_PATH,
) -> Dict[str, Any]:
    """Membaca catalog.json dan membuat dataset/splits.json."""
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    with open(catalog_path, "r", encoding="utf-8") as f:
        cat_data = json.load(f)

    videos = cat_data.get("videos", [])
    splits_dict = create_video_splits(videos)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(splits_dict, f, indent=2)

    return splits_dict


if __name__ == "__main__":
    print("Generating leak-free video splits...")
    res = generate_and_save_splits()
    print(f"Splits saved to {DEFAULT_SPLITS_PATH}:")
    print(f"  Train: {res['counts']['train']} videos")
    print(f"  Val:   {res['counts']['val']} videos")
    print(f"  Test:  {res['counts']['test']} videos (including unseen skins)")
