"""Spatial Bounding Box Annotator & Killer ROI Extractor.

Violence District Cooldown Tracker — Week 3 (Day 16)
Detects, bounds, and normalizes Killer bounding boxes (x, y, w, h) across action sequences.
Exports:
- dataset/annotations/bounding_boxes.json (Structured spatial bounding box manifest)
- dataset/extracted/labels/ (Standard YOLO-format normalized coordinate text files)
- dataset/extracted/killer_rois/ (Cropped bounding box image patches for template baseline)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


CLASS_MAP: Dict[str, int] = {
    "leap_airborne": 0,
    "leap_windup": 1,
    "leap_landing": 2,
    "negative_action": 3,
    "idle_pre_leap": 3,
    "recovery_post_leap": 3,
    "basic_attack": 3,
    "mark_action": 3,
    "chasing_movement": 3,
}


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    x_center_norm: float
    y_center_norm: float
    width_norm: float
    height_norm: float
    area: int
    aspect_ratio: float


@dataclass
class SpatialAnnotation:
    frame_id: str
    relative_image_path: str
    source_video: str
    frame_index: int
    timestamp_seconds: float
    phase: str
    label: str  # 'positive_leap' atau 'negative_action'
    class_id: int
    bbox: Optional[BoundingBox] = None
    has_detection: bool = False


@dataclass
class SpatialAnnotationManifest:
    schema_version: int = 1
    killer_id: str = "the_hidden"
    total_annotated_frames: int = 0
    total_valid_bboxes: int = 0
    class_distribution: Dict[str, int] = field(default_factory=dict)
    annotations: List[SpatialAnnotation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SpatialAnnotator:
    """Anotator spatial otomatis berbasis MOG2 background subtraction dan analisis kontur gerak."""

    def __init__(
        self,
        manifest_path: Path = Path("dataset/extracted/manifest.json"),
        output_dir: Path = Path("dataset/annotations"),
        roi_output_dir: Path = Path("dataset/extracted/killer_rois"),
        yolo_labels_dir: Path = Path("dataset/extracted/labels"),
        min_contour_area: int = 1500,
        max_contour_area_pct: float = 0.65,
    ) -> None:
        self.manifest_path = Path(manifest_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.roi_output_dir = Path(roi_output_dir).resolve()
        self.yolo_labels_dir = Path(yolo_labels_dir).resolve()
        self.min_contour_area = min_contour_area
        self.max_contour_area_pct = max_contour_area_pct

    def detect_killer_bbox(
        self,
        frame: np.ndarray,
        fgbg: cv2.BackgroundSubtractorMOG2,
    ) -> Optional[BoundingBox]:
        """Mendeteksi bounding box kontur bergerak terbesar (Killer) pada frame."""
        h, w = frame.shape[:2]
        fgmask = fgbg.apply(frame)

        # Operasi morfologi untuk menghilangkan noise kamera dan menggabungkan segmen humanoid
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cleaned = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        dilated = cv2.dilate(cleaned, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_allowed_area = int(w * h * self.max_contour_area_pct)

        valid_boxes: List[Tuple[int, int, int, int, int]] = []
        for c in contours:
            area = int(cv2.contourArea(c))
            if self.min_contour_area <= area <= max_allowed_area:
                bx, by, bw, bh = cv2.boundingRect(c)
                # Filter aspek rasio yang tidak realistis untuk humanoid
                ar = bw / float(bh) if bh > 0 else 0.0
                if 0.15 <= ar <= 3.5:
                    valid_boxes.append((bx, by, bw, bh, area))

        if not valid_boxes:
            return None

        # Pilih kontur dengan area terbesar
        bx, by, bw, bh, area = max(valid_boxes, key=lambda b: b[4])

        xc_norm = round((bx + bw / 2.0) / w, 6)
        yc_norm = round((by + bh / 2.0) / h, 6)
        w_norm = round(bw / float(w), 6)
        h_norm = round(bh / float(h), 6)
        ar = round(bw / float(bh), 3) if bh > 0 else 0.0

        return BoundingBox(
            x=bx,
            y=by,
            width=bw,
            height=bh,
            x_center_norm=xc_norm,
            y_center_norm=yc_norm,
            width_norm=w_norm,
            height_norm=h_norm,
            area=area,
            aspect_ratio=ar,
        )

    def run(self, save_rois: bool = True, save_yolo: bool = True) -> SpatialAnnotationManifest:
        """Menjalankan anotasi spasial penuh melintasi seluruh frame terekstrak."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Extracted manifest not found: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        dataset_root = self.manifest_path.parent.parent
        extracted_frames: List[Dict[str, Any]] = manifest_data.get("frames", [])

        # Kelompokkan frame berdasarkan berkas video sumber agar MOG2 background history akurat
        video_groups: Dict[str, List[Dict[str, Any]]] = {}
        for f_info in extracted_frames:
            video_groups.setdefault(f_info["source_video"], []).append(f_info)

        annotation_manifest = SpatialAnnotationManifest(
            schema_version=1,
            killer_id=manifest_data.get("killer_id", "the_hidden"),
        )

        class_dist: Dict[str, int] = {}
        total_valid = 0

        print("=" * 75)
        print(" VIOLENCE DISTRICT COOLDOWN TRACKER — SPATIAL BOUNDING BOX ANNOTATOR")
        print("=" * 75)
        print(f"Total Video Terdaftar    : {len(video_groups)}")
        print(f"Total Frame Terekstrak   : {len(extracted_frames)}")
        print(f"Simpan ROI Patch         : {'Ya' if save_rois else 'Tidak'}")
        print(f"Simpan YOLO .txt Labels  : {'Ya' if save_yolo else 'Tidak'}")
        print("-" * 75)

        for v_idx, (v_source, frames) in enumerate(video_groups.items(), 1):
            fgbg = cv2.createBackgroundSubtractorMOG2(history=30, varThreshold=25, detectShadows=False)
            v_name = Path(v_source).name
            v_valid = 0

            # Urutkan frame berdasarkan frame_index
            sorted_frames = sorted(frames, key=lambda x: x["frame_index"])

            for f_info in sorted_frames:
                rel_path = f_info.get("relative_path", "")
                f_path = dataset_root / rel_path
                if not f_path.exists():
                    continue

                frame = cv2.imread(str(f_path))
                if frame is None:
                    continue

                bbox = self.detect_killer_bbox(frame, fgbg)
                phase = f_info.get("phase", "unknown")
                label = f_info.get("label", "unknown")
                class_id = CLASS_MAP.get(phase, CLASS_MAP.get(label, 3))

                has_det = bbox is not None
                if has_det and bbox:
                    v_valid += 1
                    total_valid += 1
                    class_dist[phase] = class_dist.get(phase, 0) + 1

                    # 1. Simpan Cropped ROI jika diminta
                    if save_rois and "leap" in phase:
                        roi_dir = self.roi_output_dir / phase
                        roi_dir.mkdir(parents=True, exist_ok=True)
                        crop = frame[bbox.y : bbox.y + bbox.height, bbox.x : bbox.x + bbox.width]
                        if crop.size > 0:
                            crop_name = f"roi_{Path(rel_path).stem}.png"
                            cv2.imwrite(str(roi_dir / crop_name), crop)

                    # 2. Simpan label format YOLO (.txt) jika diminta
                    if save_yolo:
                        split = f_info.get("split", "train")
                        yolo_dir = self.yolo_labels_dir / split / label
                        yolo_dir.mkdir(parents=True, exist_ok=True)
                        label_file = yolo_dir / f"{Path(rel_path).stem}.txt"
                        yolo_content = f"{class_id} {bbox.x_center_norm:.6f} {bbox.y_center_norm:.6f} {bbox.width_norm:.6f} {bbox.height_norm:.6f}\n"
                        label_file.write_text(yolo_content, encoding="utf-8")

                annotation = SpatialAnnotation(
                    frame_id=f_info.get("frame_id", ""),
                    relative_image_path=rel_path,
                    source_video=v_source,
                    frame_index=f_info.get("frame_index", 0),
                    timestamp_seconds=f_info.get("timestamp_seconds", 0.0),
                    phase=phase,
                    label=label,
                    class_id=class_id,
                    bbox=bbox,
                    has_detection=has_det,
                )
                annotation_manifest.annotations.append(annotation)

            print(f"[{v_idx:02d}/{len(video_groups):02d}] {v_name:<34} -> {v_valid:3d}/{len(frames):3d} bboxes detected")

        annotation_manifest.total_annotated_frames = len(annotation_manifest.annotations)
        annotation_manifest.total_valid_bboxes = total_valid
        annotation_manifest.class_distribution = class_dist

        # Simpan manifest anotasi JSON
        self.output_dir.mkdir(parents=True, exist_ok=True)
        manifest_out = self.output_dir / "bounding_boxes.json"
        with open(manifest_out, "w", encoding="utf-8") as f:
            json.dump(annotation_manifest.to_dict(), f, indent=2, ensure_ascii=False)

        print("-" * 75)
        print(f"Total Frame Diproses     : {annotation_manifest.total_annotated_frames}")
        print(f"Total Bounding Box Valid : {annotation_manifest.total_valid_bboxes} ({annotation_manifest.total_valid_bboxes/max(1, annotation_manifest.total_annotated_frames)*100:.1f}%)")
        print(f"Distribusi Fase BBox     : {json.dumps(annotation_manifest.class_distribution, indent=None)}")
        print(f"Manifest JSON Tersimpan  : {manifest_out.resolve()}")
        print("=" * 75)

        return annotation_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract spatial bounding boxes and killer ROI crops.")
    parser.add_argument(
        "--manifest",
        type=str,
        default="dataset/extracted/manifest.json",
        help="Path ke manifest ekstraksi frame (default: dataset/extracted/manifest.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/annotations",
        help="Direktori output anotasi JSON (default: dataset/annotations)",
    )
    parser.add_argument(
        "--no-rois",
        action="store_true",
        help="Jangan simpan file citra potongan ROI killer",
    )
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Jangan simpan label format YOLO (.txt)",
    )
    args = parser.parse_args()

    annotator = SpatialAnnotator(
        manifest_path=Path(args.manifest),
        output_dir=Path(args.output),
    )
    annotator.run(save_rois=not args.no_rois, save_yolo=not args.no_yolo)


if __name__ == "__main__":
    main()
