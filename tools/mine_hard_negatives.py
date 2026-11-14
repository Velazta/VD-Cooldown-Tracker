"""Hard-Negative Mining Tool for The Hidden Detector.

Violence District Cooldown Tracker — Rebuild Phase 3 (Task 3.4)
Runs inference over negative gameplay footage to discover false positive detections:
- Scans negative / idle frames
- Captures false-positive 'hidden' detections (distractors like rocks, pillars, shadows, survivor clothes)
- Exports visual evidence crops to dataset/hard_negatives/
- Generates hard-negative summary report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from ultralytics import YOLO


class HardNegativeMiner:
    def __init__(
        self,
        model_path: Path,
        dataset_dir: Path = Path("dataset/yolo"),
        output_dir: Path = Path("dataset/hard_negatives"),
        conf_threshold: float = 0.25,
        imgsz: int = 960,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found: {self.model_path}")

        self.dataset_dir = Path(dataset_dir)
        self.output_dir = Path(output_dir)
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = YOLO(str(self.model_path))

    def run_mining(self, split: str = "train") -> Dict[str, Any]:
        img_dir = self.dataset_dir / "images" / split
        lbl_dir = self.dataset_dir / "labels" / split

        if not img_dir.exists():
            raise FileNotFoundError(f"Directory not found: {img_dir}")

        image_paths = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
        print(f"Scanning {len(image_paths)} images in {split} for hard negatives...")

        false_positives: List[Dict[str, Any]] = []

        for p in image_paths:
            # Check ground truth label
            lbl_p = lbl_dir / f"{p.stem}.txt"
            has_ground_truth_hidden = False
            if lbl_p.exists():
                content = lbl_p.read_text(encoding="utf-8").strip()
                if content:
                    for line in content.splitlines():
                        if line.startswith("0 "):  # Class 0: Hidden
                            has_ground_truth_hidden = True
                            break

            # If ground truth does NOT contain Hidden, any Hidden prediction is a False Positive!
            if not has_ground_truth_hidden:
                results = self.model.predict(
                    source=str(p),
                    conf=self.conf_threshold,
                    imgsz=self.imgsz,
                    verbose=False,
                )

                res = results[0]
                if res.boxes is not None and len(res.boxes) > 0:
                    for idx, box in enumerate(res.boxes):
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())

                        if cls_id == 0:  # Predicted as Hidden on a negative frame!
                            xyxy = box.xyxy[0].cpu().numpy().astype(int)
                            x1, y1, x2, y2 = xyxy

                            orig_img = cv2.imread(str(p))
                            h, w = orig_img.shape[:2]
                            cx1, cy1 = max(0, x1), max(0, y1)
                            cx2, cy2 = min(w, x2), min(h, y2)
                            crop = orig_img[cy1:cy2, cx1:cx2]

                            crop_name = f"fp_{p.stem}_box{idx}_conf{int(conf*100)}.jpg"
                            crop_path = self.output_dir / crop_name
                            if crop.size > 0:
                                cv2.imwrite(str(crop_path), crop)

                            fp_record = {
                                "source_image": p.name,
                                "crop_file": crop_name,
                                "confidence": round(conf, 3),
                                "bbox_xyxy": [int(x1), int(y1), int(x2), int(y2)],
                            }
                            false_positives.append(fp_record)
                            print(f"  [FP FOUND] {p.name}: conf {conf*100:.1f}% -> saved to {crop_name}")

        report = {
            "model_path": str(self.model_path),
            "split_scanned": split,
            "images_scanned": len(image_paths),
            "false_positives_found": len(false_positives),
            "items": false_positives,
        }

        report_path = self.output_dir / "mining_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print("\n" + "=" * 60)
        print("HARD-NEGATIVE MINING COMPLETE")
        print("=" * 60)
        print(f"Images Scanned:        {len(image_paths)}")
        print(f"False Positives Found: {len(false_positives)}")
        print(f"Report JSON:           {report_path}")
        print("=" * 60)

        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine hard negatives from negative footage.")
    parser.add_argument("--model", required=True, help="Path to trained model checkpoint (.pt)")
    parser.add_argument("--dataset", default="dataset/yolo", help="Path to YOLO dataset directory")
    parser.add_argument("--output", default="dataset/hard_negatives", help="Directory to save false positive crops")
    parser.add_argument("--split", default="train", help="Split to scan")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--imgsz", type=int, default=960, help="Image resolution")

    args = parser.parse_args()

    miner = HardNegativeMiner(
        model_path=Path(args.model),
        dataset_dir=Path(args.dataset),
        output_dir=Path(args.output),
        conf_threshold=args.conf,
        imgsz=args.imgsz,
    )
    miner.run_mining(split=args.split)


if __name__ == "__main__":
    main()
