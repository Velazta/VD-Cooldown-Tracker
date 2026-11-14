"""Dataset Extractor v2 (Live ROI & Ultralytics Compliant).

Violence District Cooldown Tracker — Rebuild Phase 1 (Task 1.2)
Extracts frames according to:
- Exact ROI cropping matching live app_config.json
- Dual-rate temporal sampling: native FPS in skill windows (+-1s), 2-5 FPS in negative/idle regions
- Perceptual deduplication via difference hashing (dHash)
- Leak-free split assignment from dataset/splits.json
- Ultralytics-compliant folder structure: dataset/yolo/images/{split} and dataset/yolo/labels/{split}
- Full metadata tracking in dataset/yolo/metadata.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np


def compute_dhash(image: np.ndarray, hash_size: int = 8) -> int:
    """Computes 64-bit difference hash (dHash) from an image.
    
    Resizes image to (hash_size + 1, hash_size), converts to grayscale,
    and computes horizontal pixel differences.
    """
    if image is None or image.size == 0:
        return 0
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    val = 0
    for b in diff.flatten():
        val = (val << 1) | int(b)
    return val


def hamming_distance(h1: int, h2: int) -> int:
    """Computes Hamming distance between two integer bit hashes."""
    return bin(h1 ^ h2).count("1")


def infer_skin_id(video_name: str) -> str:
    """Infers skin ID string from video file name."""
    name_lower = video_name.lower()
    m = re.search(r"hidden_skin(\d+)", name_lower)
    if m:
        return f"skin_{m.group(1)}"
    m2 = re.search(r"hidden(\d+)", name_lower)
    if m2:
        return f"skin_{m2.group(1)}"
    return "skin_base"


@dataclass
class FrameRecord:
    frame_id: str
    video_name: str
    frame_index: int
    timestamp_seconds: float
    split: str
    skin_id: str
    in_skill_window: bool
    ability: Optional[str]
    dhash: str
    image_relpath: str
    label_relpath: str
    crop_width: int
    crop_height: int


class DatasetExtractorV2:
    def __init__(
        self,
        config_path: Path = Path("config/app_config.json"),
        splits_path: Path = Path("dataset/splits.json"),
        temporal_path: Path = Path("dataset/temporal_annotations.json"),
        video_dir: Path = Path("database/dataset/HIDDEN/MP4/SURVIVOR CAM"),
        output_dir: Path = Path("dataset/yolo"),
        window_seconds: float = 1.0,
        negative_fps: float = 3.0,
        dhash_threshold: int = 2,
    ) -> None:
        self.config_path = Path(config_path)
        self.splits_path = Path(splits_path)
        self.temporal_path = Path(temporal_path)
        self.video_dir = Path(video_dir)
        self.output_dir = Path(output_dir)
        self.window_seconds = window_seconds
        self.negative_fps = negative_fps
        self.dhash_threshold = dhash_threshold

        self.roi_config = self._load_roi_config()
        self.splits = self._load_splits()
        self.temporal = self._load_temporal()

    def _load_roi_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {"x": 130, "y": 10, "width": 1540, "height": 580, "enabled": True}
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("capture", {}).get("roi", {"x": 130, "y": 10, "width": 1540, "height": 580, "enabled": True})

    def _load_splits(self) -> Dict[str, str]:
        if not self.splits_path.exists():
            return {}
        with open(self.splits_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("video_to_split", {})

    def _load_temporal(self) -> Dict[str, Any]:
        if not self.temporal_path.exists():
            return {}
        with open(self.temporal_path, "r", encoding="utf-8") as f:
            return json.load(f).get("videos", {})

    def crop_frame(self, frame: np.ndarray, ref_width: int = 1920, ref_height: int = 1032) -> np.ndarray:
        """Crops frame according to live ROI, scaling proportionally if frame size differs from reference."""
        if not self.roi_config.get("enabled", True):
            return frame

        fh, fw = frame.shape[:2]
        rx = self.roi_config.get("x", 130)
        ry = self.roi_config.get("y", 10)
        rw = self.roi_config.get("width", 1540)
        rh = self.roi_config.get("height", 580)

        if fw == ref_width and fh == ref_height:
            # Exact match to reference resolution
            cx = max(0, min(rx, fw - 1))
            cy = max(0, min(ry, fh - 1))
            cw = max(1, min(rw, fw - cx))
            ch = max(1, min(rh, fh - cy))
        else:
            # Scale proportionally
            scale_x = fw / ref_width
            scale_y = fh / ref_height
            cx = max(0, min(int(round(rx * scale_x)), fw - 1))
            cy = max(0, min(int(round(ry * scale_y)), fh - 1))
            cw = max(1, min(int(round(rw * scale_x)), fw - cx))
            ch = max(1, min(int(round(rh * scale_y)), fh - cy))

        return frame[cy : cy + ch, cx : cx + cw]

    def get_skill_windows(self, video_name: str, fps: float) -> List[Tuple[int, int, str]]:
        """Returns list of (start_frame, end_frame, ability) for skill windows in this video."""
        vid_info = self.temporal.get(video_name, {})
        windows: List[Tuple[int, int, str]] = []
        half_win = int(round(self.window_seconds * fps))

        # Check explicit events
        events = vid_info.get("events", [])
        for ev in events:
            cast_f = ev.get("cast_start_frame", 0)
            ability = ev.get("ability", "unknown")
            windows.append((max(0, cast_f - half_win), cast_f + half_win, ability))

        # Fallback to active_leap_window if no events present
        if not windows and "active_leap_window" in vid_info:
            alw = vid_info["active_leap_window"]
            s = alw.get("start_frame", 0)
            e = alw.get("end_frame", 0)
            windows.append((max(0, s - half_win), e + half_win, "leap"))

        return windows

    def is_in_skill_window(self, frame_idx: int, windows: List[Tuple[int, int, str]]) -> Tuple[bool, Optional[str]]:
        for sf, ef, ab in windows:
            if sf <= frame_idx <= ef:
                return True, ab
        return False, None

    def extract_video(
        self,
        video_path: Path,
        split: str,
    ) -> List[FrameRecord]:
        video_name = video_path.name
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Warning: Failed to open video: {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        windows = self.get_skill_windows(video_name, fps)
        skin_id = infer_skin_id(video_name)

        neg_step = max(1, int(round(fps / self.negative_fps)))
        records: List[FrameRecord] = []
        last_dhash: Optional[int] = None
        frame_idx = 0

        # Destination directories for this split
        img_dir = self.output_dir / "images" / split
        lbl_dir = self.output_dir / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            in_skill, ability = self.is_in_skill_window(frame_idx, windows)

            # Sample rate check: skill window -> 100% native FPS; non-skill -> negative_fps
            if not in_skill and (frame_idx % neg_step != 0):
                frame_idx += 1
                continue

            cropped = self.crop_frame(frame)
            ch, cw = cropped.shape[:2]

            # Perceptual hash deduplication
            curr_hash = compute_dhash(cropped)
            if last_dhash is not None and hamming_distance(curr_hash, last_dhash) <= self.dhash_threshold:
                # Near duplicate, skip unless skill start frame
                frame_idx += 1
                continue

            last_dhash = curr_hash
            ts = frame_idx / fps

            # Save frame image
            base_stem = f"{video_path.stem}_f{frame_idx:05d}"
            img_filename = f"{base_stem}.jpg"
            lbl_filename = f"{base_stem}.txt"

            img_path = img_dir / img_filename
            lbl_path = lbl_dir / lbl_filename

            cv2.imwrite(str(img_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Ensure corresponding label file exists (empty placeholder for background until labeled)
            if not lbl_path.exists():
                lbl_path.write_text("", encoding="utf-8")

            rel_img = f"images/{split}/{img_filename}"
            rel_lbl = f"labels/{split}/{lbl_filename}"

            record = FrameRecord(
                frame_id=base_stem,
                video_name=video_name,
                frame_index=frame_idx,
                timestamp_seconds=round(ts, 3),
                split=split,
                skin_id=skin_id,
                in_skill_window=in_skill,
                ability=ability,
                dhash=f"{curr_hash:016x}",
                image_relpath=rel_img,
                label_relpath=rel_lbl,
                crop_width=cw,
                crop_height=ch,
            )
            records.append(record)
            frame_idx += 1

        cap.release()
        return records

    def run(self) -> Dict[str, Any]:
        """Runs full dataset extraction across all videos found in splits."""
        print(f"Starting Extraction v2 to {self.output_dir}...")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        all_records: List[FrameRecord] = []
        counts: Dict[str, int] = {"train": 0, "val": 0, "test": 0}

        # Find all MP4s in video_dir (recursive search if needed)
        found_videos: Dict[str, Path] = {}
        for p in self.video_dir.rglob("*.mp4"):
            found_videos[p.name] = p

        if not found_videos:
            raise FileNotFoundError(f"No video files found in {self.video_dir}")

        for video_name, split in self.splits.items():
            if video_name not in found_videos:
                print(f"Warning: Video {video_name} listed in splits.json not found in {self.video_dir}")
                continue

            vid_path = found_videos[video_name]
            records = self.extract_video(vid_path, split)
            all_records.extend(records)
            counts[split] = counts.get(split, 0) + len(records)
            print(f"  [{split.upper()}] {video_name}: {len(records)} frames extracted")

        # Write metadata
        metadata = {
            "schema_version": 2,
            "total_frames": len(all_records),
            "counts": counts,
            "roi_config": self.roi_config,
            "dhash_threshold": self.dhash_threshold,
            "negative_fps": self.negative_fps,
            "frames": [asdict(r) for r in all_records],
        }

        meta_path = self.output_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"\nExtraction complete! Total frames: {len(all_records)}")
        print(f"  Train: {counts.get('train', 0)}")
        print(f"  Val:   {counts.get('val', 0)}")
        print(f"  Test:  {counts.get('test', 0)}")
        print(f"Metadata saved to: {meta_path}")

        return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract video dataset according to live ROI and Ultralytics format.")
    parser.add_argument("--config", default="config/app_config.json", help="Path to app_config.json")
    parser.add_argument("--splits", default="dataset/splits.json", help="Path to splits.json")
    parser.add_argument("--temporal", default="dataset/temporal_annotations.json", help="Path to temporal_annotations.json")
    parser.add_argument("--video-dir", default="database/dataset/HIDDEN/MP4/SURVIVOR CAM", help="Directory of source MP4 videos")
    parser.add_argument("--output-dir", default="dataset/yolo", help="Directory to save YOLO dataset")
    parser.add_argument("--window-sec", type=float, default=1.0, help="Skill window duration (+- seconds around event)")
    parser.add_argument("--neg-fps", type=float, default=3.0, help="Sample rate for frames outside skill window")
    parser.add_argument("--dhash-thresh", type=int, default=2, help="Max Hamming distance to treat as near-duplicate")

    args = parser.parse_args()

    extractor = DatasetExtractorV2(
        config_path=Path(args.config),
        splits_path=Path(args.splits),
        temporal_path=Path(args.temporal),
        video_dir=Path(args.video_dir),
        output_dir=Path(args.output_dir),
        window_seconds=args.window_sec,
        negative_fps=args.neg_fps,
        dhash_threshold=args.dhash_thresh,
    )
    extractor.run()


if __name__ == "__main__":
    main()
