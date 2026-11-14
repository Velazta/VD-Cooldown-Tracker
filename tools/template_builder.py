"""Canonical Action Template Builder for The Hidden.

Violence District Cooldown Tracker — Week 3 (Day 16)
Selects and exports normalized canonical ROI templates (airborne, windup, landing, attack, mark)
for Day 17 OpenCV template matching baseline evaluation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class TemplateEntry:
    template_id: str
    phase: str
    action_type: str
    source_frame_id: str
    width: int
    height: int
    aspect_ratio: float
    relative_path: str


@dataclass
class TemplateManifest:
    schema_version: int = 1
    killer_id: str = "the_hidden"
    total_templates: int = 0
    templates: List[TemplateEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TemplateBuilder:
    """Pembuat pustaka template visual acuan untuk The Hidden."""

    def __init__(
        self,
        bounding_boxes_path: Path = Path("dataset/annotations/bounding_boxes.json"),
        output_dir: Path = Path("dataset/templates/the_hidden"),
    ) -> None:
        p = Path(bounding_boxes_path)
        if not p.exists() and Path("dataset/legacy_mog2/bounding_boxes.json").exists():
            import warnings
            warnings.warn(
                "TemplateBuilder reading legacy MOG2 bounding boxes! Marked invalid_mog2_source.",
                UserWarning,
                stacklevel=2,
            )
            p = Path("dataset/legacy_mog2/bounding_boxes.json")
        self.bounding_boxes_path = p.resolve()
        self.output_dir = Path(output_dir).resolve()

    def build_templates(self) -> TemplateManifest:
        """Memilih bounding box terbaik dari setiap fase aksi untuk dijadikan template acuan."""
        if not self.bounding_boxes_path.exists():
            raise FileNotFoundError(f"Annotations not found at: {self.bounding_boxes_path}")

        with open(self.bounding_boxes_path, "r", encoding="utf-8") as f:
            bbox_data = json.load(f)

        dataset_root = self.bounding_boxes_path.parent.parent
        annotations = bbox_data.get("annotations", [])

        # Kumpulkan kandidat bounding box per fase
        candidates_by_phase: Dict[str, List[Dict[str, Any]]] = {}
        for a in annotations:
            if a.get("has_detection") and a.get("bbox"):
                phase = a.get("phase", "unknown")
                candidates_by_phase.setdefault(phase, []).append(a)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        manifest = TemplateManifest(schema_version=1)

        # Fase-fase krusial yang memerlukan template acuan
        target_phases = [
            ("leap_airborne", "leap_action"),
            ("leap_windup", "leap_action"),
            ("leap_landing", "leap_action"),
            ("hit_survivor", "basic_attack"),
            ("hit_wall", "basic_attack"),
            ("mark_solo", "mark_action"),
            ("idle_pre_leap", "idle_baseline"),
        ]

        print("=" * 75)
        print(" VIOLENCE DISTRICT COOLDOWN TRACKER — TEMPLATE LIBRARY BUILDER")
        print("=" * 75)
        print(f"Direktori Output Template: {self.output_dir}")
        print("-" * 75)

        for phase, action_type in target_phases:
            items = candidates_by_phase.get(phase, [])
            if not items:
                continue

            # Filter kandidat dengan dimensi humanoid yang realistis (bukan artifak kibasan kamera layar penuh)
            realistic_items = [
                x for x in items
                if 50 <= x["bbox"]["width"] <= 500
                and 70 <= x["bbox"]["height"] <= 600
                and 0.20 <= x["bbox"]["aspect_ratio"] <= 1.60
            ]
            eval_items = realistic_items if realistic_items else items
            sorted_items = sorted(eval_items, key=lambda x: x["bbox"]["area"], reverse=True)
            top_samples = sorted_items[:2]

            for rank, item in enumerate(top_samples, 1):
                rel_img = item.get("relative_image_path", "")
                img_path = dataset_root / rel_img
                if not img_path.exists():
                    continue

                frame = cv2.imread(str(img_path))
                if frame is None:
                    continue

                bbox = item["bbox"]
                bx, by, bw, bh = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                crop = frame[by : by + bh, bx : bx + bw]
                if crop.size == 0:
                    continue

                tmpl_id = f"template_{phase}_var{rank}"
                out_name = f"{tmpl_id}.png"
                out_path = self.output_dir / out_name
                cv2.imwrite(str(out_path), crop)

                ar = round(bw / float(bh), 3) if bh > 0 else 0.0
                rel_tmpl_path = str(out_path.relative_to(dataset_root)).replace("\\", "/")

                entry = TemplateEntry(
                    template_id=tmpl_id,
                    phase=phase,
                    action_type=action_type,
                    source_frame_id=item.get("frame_id", ""),
                    width=bw,
                    height=bh,
                    aspect_ratio=ar,
                    relative_path=rel_tmpl_path,
                )
                manifest.templates.append(entry)
                print(f"[TEMPLATE] {tmpl_id:<26} | {bw}x{bh} (ar={ar:4.2f}) | Source: {item.get('frame_id')}")

        manifest.total_templates = len(manifest.templates)
        manifest_path = self.output_dir / "templates_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

        print("-" * 75)
        print(f"Total Template Diekstrak : {manifest.total_templates}")
        print(f"Manifest Template        : {manifest_path.resolve()}")
        print("=" * 75)

        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build canonical visual templates for killer actions.")
    parser.add_argument(
        "--bboxes",
        type=str,
        default="dataset/annotations/bounding_boxes.json",
        help="Path ke bounding_boxes.json (default: dataset/annotations/bounding_boxes.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/templates/the_hidden",
        help="Direktori penyimpanan template acuan (default: dataset/templates/the_hidden)",
    )
    args = parser.parse_args()

    builder = TemplateBuilder(
        bounding_boxes_path=Path(args.bboxes),
        output_dir=Path(args.output),
    )
    builder.build_templates()


if __name__ == "__main__":
    main()
