"""Dataset Frame Extractor & Action Segment Slicer (V2).

Violence District Cooldown Tracker — Week 3 (Day 15 Langkah 2 Enhanced)
Extracts, samples, and organizes video frames from catalogued MP4 gameplay footage
into structured train/val/test splits with:
- Temporal Action Window Boundary support (eliminates label noise from pre/post idle)
- Action Phase tagging (leap_windup, leap_airborne, leap_landing, idle_pre_leap, recovery_post_leap)
- Intelligent negative class balancing & capping on long repetitive chasing footage
- Temporal motion difference calculation per frame
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


def compute_sha256_bytes(data: bytes) -> str:
    """Menghitung hash SHA-256 dari bytes dalam memori."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class FrameMetadata:
    frame_id: str
    relative_path: str
    source_video: str
    frame_index: int
    timestamp_seconds: float
    label: str  # 'positive_leap' atau 'negative_action'
    category: str  # 'leap_action', 'basic_attack', 'mark_action', 'chasing_movement'
    sub_category: str  # 'leap_airborne', 'leap_windup', 'leap_landing', 'hit_wall', dsb.
    phase: str  # Fase temporal aksi
    split: str  # 'train', 'val', 'test'
    motion_diff: float  # Perbedaan piksel absolut rata-rata terhadap frame sebelumnya
    width: int
    height: int
    file_size_bytes: int
    sha256: str


@dataclass
class ExtractionManifest:
    schema_version: int = 2
    killer_id: str = "the_hidden"
    target_fps: float = 10.0
    image_format: str = "jpg"
    total_frames_extracted: int = 0
    positive_leap_frames: int = 0
    negative_action_frames: int = 0
    train_frames: int = 0
    val_frames: int = 0
    test_frames: int = 0
    leap_phases_distribution: Dict[str, int] = field(default_factory=dict)
    frames: List[FrameMetadata] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FrameExtractor:
    """Ekstraktor frame video cerdas dengan temporal windowing dan penyeimbang kelas."""

    def __init__(
        self,
        catalog_path: Path = Path("dataset/catalog.json"),
        temporal_annotations_path: Optional[Path] = Path("dataset/temporal_annotations.json"),
        output_dir: Path = Path("dataset/extracted"),
        target_fps: float = 10.0,
        image_format: str = "jpg",
        max_chasing_frames: int = 45,
        max_frames_per_video: Optional[int] = None,
        jpeg_quality: int = 95,
    ) -> None:
        self.catalog_path = Path(catalog_path).resolve()
        self.temporal_annotations_path = Path(temporal_annotations_path).resolve() if temporal_annotations_path else None
        self.output_dir = Path(output_dir).resolve()
        self.target_fps = target_fps
        self.image_format = image_format.lower().lstrip(".")
        self.max_chasing_frames = max_chasing_frames
        self.max_frames_per_video = max_frames_per_video
        self.jpeg_quality = jpeg_quality
        self.temporal_annotations: Dict[str, Any] = self.load_temporal_annotations()

    def load_catalog(self) -> Dict[str, Any]:
        """Memuat katalog JSON."""
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog JSON not found at: {self.catalog_path}")
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_temporal_annotations(self) -> Dict[str, Any]:
        """Memuat anotasi jendela aksi temporal (ground truth Leap windows)."""
        if self.temporal_annotations_path and self.temporal_annotations_path.exists():
            try:
                with open(self.temporal_annotations_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("videos", {})
            except Exception:
                return {}
        return {}

    def get_frame_annotation(
        self,
        video_name: str,
        frame_idx: int,
        fallback_is_pos: bool,
        fallback_sub_cat: str,
    ) -> Tuple[str, str, str]:
        """Menentukan label persis, sub-kategori, dan fase aksi berdasarkan anotasi temporal.

        Returns:
            Tuple[label, sub_category, phase]
        """
        video_annot = self.temporal_annotations.get(video_name)
        if video_annot and "phases" in video_annot:
            for p in video_annot["phases"]:
                if p["start_frame"] <= frame_idx <= p["end_frame"]:
                    phase_name = p["phase"]
                    is_leap = p.get("is_leap", False)
                    label = "positive_leap" if is_leap else "negative_action"
                    return label, phase_name, phase_name

        # Fallback jika tidak ada anotasi granular
        label = "positive_leap" if fallback_is_pos else "negative_action"
        return label, fallback_sub_cat, fallback_sub_cat

    def extract_from_video(
        self,
        video_info: Dict[str, Any],
        video_file_path: Path,
    ) -> Tuple[List[FrameMetadata], float, int]:
        """Mengekstrak frame dari berkas video tunggal berdasarkan konfigurasi sampling dan jendela temporal.

        Returns:
            Tuple[List[FrameMetadata], peak_motion_diff, peak_motion_frame_index]
        """
        cap = cv2.VideoCapture(str(video_file_path))
        if not cap.isOpened():
            return [], 0.0, 0

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0 or total_fc <= 0:
            cap.release()
            return [], 0.0, 0

        # Tentukan interval sampling (step)
        if self.target_fps > 0 and fps > self.target_fps:
            step = max(1, round(fps / self.target_fps))
        else:
            step = 1

        split = video_info.get("split", "train")
        category = video_info.get("category", "unclassified")
        fallback_sub_cat = video_info.get("sub_category", "unknown")
        fallback_is_pos = video_info.get("is_positive_leap", False)
        video_stem = video_file_path.stem
        video_name = video_file_path.name

        # Tentukan batas maksimal frame khusus untuk video chasing panjang
        if category == "chasing_movement" and self.max_chasing_frames:
            effective_max_frames = self.max_chasing_frames
        else:
            effective_max_frames = self.max_frames_per_video

        frames_meta: List[FrameMetadata] = []
        prev_gray: Optional[np.ndarray] = None
        max_motion = 0.0
        peak_frame_idx = 0
        extracted_count = 0

        for frame_idx in range(total_fc):
            ret, frame = cap.read()
            if not ret:
                break

            # Hitung motion delta jika frame diproses
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                motion_diff = float(cv2.absdiff(gray, prev_gray).mean())
            else:
                motion_diff = 0.0
            prev_gray = gray

            if motion_diff > max_motion:
                max_motion = motion_diff
                peak_frame_idx = frame_idx

            # Periksa apakah frame ini dijadwalkan untuk diekstrak
            if frame_idx % step != 0:
                continue

            if effective_max_frames is not None and extracted_count >= effective_max_frames:
                break

            # Tentukan label dan fase persis via temporal windowing
            label, sub_cat, phase = self.get_frame_annotation(
                video_name=video_name,
                frame_idx=frame_idx,
                fallback_is_pos=fallback_is_pos,
                fallback_sub_cat=fallback_sub_cat,
            )

            target_dir = self.output_dir / split / label
            target_dir.mkdir(parents=True, exist_ok=True)

            timestamp = round(frame_idx / fps, 3)
            ext = self.image_format
            file_name = f"{video_stem}_f{frame_idx:05d}.{ext}"
            dest_path = target_dir / file_name

            # Encode citra
            if ext in ("jpg", "jpeg"):
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            else:
                encode_params = []

            success, encoded_img = cv2.imencode(f".{ext}", frame, encode_params)
            if not success:
                continue

            img_bytes = encoded_img.tobytes()
            dest_path.write_bytes(img_bytes)
            sha256_hash = compute_sha256_bytes(img_bytes)

            try:
                rel_path = str(dest_path.relative_to(self.output_dir.parent))
            except ValueError:
                rel_path = str(dest_path)

            h, w = frame.shape[:2]
            frames_meta.append(
                FrameMetadata(
                    frame_id=file_name,
                    relative_path=rel_path.replace("\\", "/"),
                    source_video=video_info.get("relative_path", str(video_file_path)),
                    frame_index=frame_idx,
                    timestamp_seconds=timestamp,
                    label=label,
                    category=category,
                    sub_category=sub_cat,
                    phase=phase,
                    split=split,
                    motion_diff=round(motion_diff, 2),
                    width=w,
                    height=h,
                    file_size_bytes=len(img_bytes),
                    sha256=sha256_hash,
                )
            )
            extracted_count += 1

        cap.release()
        return frames_meta, round(max_motion, 2), peak_frame_idx

    def run(self, filter_substr: Optional[str] = None) -> ExtractionManifest:
        """Mengeksekusi proses ekstraksi frame untuk seluruh video yang terdaftar di katalog."""
        catalog_data = self.load_catalog()
        videos = catalog_data.get("videos", [])

        manifest = ExtractionManifest(
            schema_version=2,
            killer_id=catalog_data.get("killer_id", "the_hidden"),
            target_fps=self.target_fps,
            image_format=self.image_format,
        )

        project_root = self.catalog_path.parent.parent

        print("=" * 75)
        print(" VIOLENCE DISTRICT COOLDOWN TRACKER — FRAME EXTRACTOR (V2 TEMPORAL)")
        print("=" * 75)
        print(f"Target FPS Sampling   : {self.target_fps:.1f} FPS" if self.target_fps > 0 else "All Frames")
        print(f"Format Citra          : {self.image_format.upper()} (q={self.jpeg_quality})")
        print(f"Output Directory      : {self.output_dir}")
        print(f"Temporal Annotations  : {len(self.temporal_annotations)} video beranotasi presisi")
        print(f"Batas Maks Chasing    : {self.max_chasing_frames} frame/video (penyeimbang kelas)")
        print("-" * 75)

        phase_counts: Dict[str, int] = {}

        for idx, v_info in enumerate(videos, 1):
            rel_v_path = v_info.get("relative_path", "")
            video_file = project_root / rel_v_path
            if not video_file.exists():
                video_file = Path(rel_v_path).resolve()

            if filter_substr and filter_substr.lower() not in video_file.name.lower():
                continue

            frames, max_motion, peak_idx = self.extract_from_video(v_info, video_file)
            manifest.frames.extend(frames)

            # Hitung distribusi fase
            for f in frames:
                phase_counts[f.phase] = phase_counts.get(f.phase, 0) + 1

            has_annot = video_file.name in self.temporal_annotations
            tag = "[LEAP-TEMP]" if has_annot else ("[LEAP-RAW ]" if v_info.get("is_positive_leap", False) else "[NEGATIVE ]")
            print(
                f"[{idx:02d}/{len(videos):02d}] {tag} {video_file.name:<32} -> "
                f"{len(frames):3d} frames (Peak Motion: {max_motion:5.2f} at f#{peak_idx})"
            )

        # Agregasi statistik manifest
        manifest.total_frames_extracted = len(manifest.frames)
        manifest.positive_leap_frames = sum(1 for f in manifest.frames if f.label == "positive_leap")
        manifest.negative_action_frames = sum(1 for f in manifest.frames if f.label == "negative_action")
        manifest.train_frames = sum(1 for f in manifest.frames if f.split == "train")
        manifest.val_frames = sum(1 for f in manifest.frames if f.split == "val")
        manifest.test_frames = sum(1 for f in manifest.frames if f.split == "test")
        manifest.leap_phases_distribution = phase_counts

        # Simpan manifest JSON
        manifest_path = self.output_dir / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

        print("-" * 75)
        print(f"Total Frame Terekstrak : {manifest.total_frames_extracted}")
        print(f"Positive Leap Frames   : {manifest.positive_leap_frames} (Windup, Airborne, Landing)")
        print(f"Negative Action Frames : {manifest.negative_action_frames} (Attacks, Marks, Chasing, Pre/Post-Idle)")
        print(f"Rasio Keseimbangan     : 1 : {manifest.negative_action_frames / max(1, manifest.positive_leap_frames):.1f}")
        print(f"Distribusi Split       : Train={manifest.train_frames} | Val={manifest.val_frames} | Test={manifest.test_frames}")
        print(f"Fase-fase Aksi         : {json.dumps(manifest.leap_phases_distribution, indent=None)}")
        print(f"Manifest JSON          : {manifest_path.resolve()}")
        print("=" * 75)

        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract video frames with temporal action windows.")
    parser.add_argument(
        "--catalog",
        type=str,
        default="dataset/catalog.json",
        help="Path ke berkas catalog.json (default: dataset/catalog.json)",
    )
    parser.add_argument(
        "--annotations",
        type=str,
        default="dataset/temporal_annotations.json",
        help="Path ke berkas temporal_annotations.json (default: dataset/temporal_annotations.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/extracted",
        help="Direktori penyimpanan hasil ekstraksi frame (default: dataset/extracted)",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=10.0,
        help="Target frame rate sampling (default: 10.0 FPS, 0 untuk semua frame)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["jpg", "png"],
        default="jpg",
        help="Format citra output (default: jpg)",
    )
    parser.add_argument(
        "--max-chasing",
        type=int,
        default=45,
        help="Batas maksimal frame untuk video chasing panjang (default: 45)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Batas maksimal frame per video secara umum (opsional)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filter nama berkas video (misal: 'leap' untuk hanya video leap)",
    )
    args = parser.parse_args()

    extractor = FrameExtractor(
        catalog_path=Path(args.catalog),
        temporal_annotations_path=Path(args.annotations) if args.annotations else None,
        output_dir=Path(args.output),
        target_fps=args.target_fps,
        image_format=args.format,
        max_chasing_frames=args.max_chasing,
        max_frames_per_video=args.max_frames,
    )
    extractor.run(filter_substr=args.filter)


if __name__ == "__main__":
    main()
