"""Controlled YOLO Detector Training Script.

Violence District Cooldown Tracker — Rebuild Phase 3 (Task 3.2)
Executes reproducible YOLO entity detector training (hidden vs survivor) with:
- Fixed random seeds
- Small-object optimized input resolution (imgsz: 640 / 960 / 1280)
- Automatic validation on test split (zero-leakage unseen videos)
- Automatic ONNX model export for low-latency desktop inference
- Comprehensive evaluation logging to training/REPORT.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from ultralytics import YOLO

from tools.validate_yolo_dataset import validate_yolo_dataset


def run_training_experiment(
    data_yaml: Path = Path("training/data.yaml"),
    model_name: str = "yolov8n.pt",
    imgsz: int = 960,
    epochs: int = 30,
    batch_size: int = 8,
    seed: int = 42,
    device: Optional[str] = None,
    project_dir: Path = Path("dataset/runs/train"),
    experiment_name: str = "yolov8n_smallobj_960",
    export_onnx: bool = True,
) -> Dict[str, Any]:
    print("=" * 60)
    print("STARTING CONTROLLED DETECTOR TRAINING EXPERIMENT")
    print("=" * 60)
    print(f"Model:       {model_name}")
    print(f"Data:        {data_yaml}")
    print(f"Resolution:  {imgsz}x{imgsz}")
    print(f"Epochs:      {epochs}")
    print(f"Batch size:  {batch_size}")
    print(f"Seed:        {seed}")
    print(f"Device:      {device or ('cuda:0' if torch.cuda.is_available() else 'cpu')}")
    print(f"Project:     {project_dir} / {experiment_name}")
    print("=" * 60)

    # 1. Dataset verification
    is_valid, errors, stats = validate_yolo_dataset(data_yaml_out=data_yaml)
    if not is_valid:
        raise RuntimeError(f"Dataset validation failed with errors: {errors}")

    start_time = time.time()

    # 2. Initialize YOLO model
    model = YOLO(model_name)

    # 3. Training arguments tailored for Roblox small-object companion detection
    resolved_device = device if device else (0 if torch.cuda.is_available() else "cpu")
    train_results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        seed=seed,
        device=resolved_device,
        project=str(project_dir),
        name=experiment_name,
        exist_ok=True,
        # Small object augmentations
        mosaic=1.0,
        fliplr=0.5,
        scale=0.5,
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.4,
        verbose=True,
    )

    elapsed_time = round(time.time() - start_time, 2)
    print(f"\nTraining completed in {elapsed_time:.1f}s.")

    # 4. Evaluation on Validation Split
    print("\nEvaluating on Validation Split...")
    val_metrics = model.val(data=str(data_yaml), split="val", imgsz=imgsz, device=resolved_device)

    # 5. Evaluation on Test Split (Unseen Videos & Unseen Skins)
    print("\nEvaluating on Test Split (Unseen footage)...")
    test_metrics = model.val(data=str(data_yaml), split="test", imgsz=imgsz, device=resolved_device)

    # Extract metrics
    val_map50 = float(val_metrics.box.map50) if hasattr(val_metrics.box, "map50") else 0.0
    val_map = float(val_metrics.box.map) if hasattr(val_metrics.box, "map") else 0.0
    test_map50 = float(test_metrics.box.map50) if hasattr(test_metrics.box, "map50") else 0.0
    test_map = float(test_metrics.box.map) if hasattr(test_metrics.box, "map") else 0.0

    save_dir = Path(train_results.save_dir) if hasattr(train_results, "save_dir") else project_dir / experiment_name
    best_weights_path = save_dir / "weights" / "best.pt"
    onnx_path: Optional[Path] = None

    # 6. Export to ONNX if requested
    if export_onnx and best_weights_path.exists():
        print(f"\nExporting best weights to ONNX ({best_weights_path})...")
        best_model = YOLO(str(best_weights_path))
        onnx_file_str = best_model.export(format="onnx", imgsz=imgsz, dynamic=False)
        onnx_path = Path(onnx_file_str)
        print(f"ONNX exported successfully: {onnx_path}")

    experiment_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_name": model_name,
        "imgsz": imgsz,
        "epochs": epochs,
        "batch_size": batch_size,
        "seed": seed,
        "elapsed_seconds": elapsed_time,
        "val_map50": round(val_map50, 4),
        "val_map50_95": round(val_map, 4),
        "test_map50": round(test_map50, 4),
        "test_map50_95": round(test_map, 4),
        "weights_path": str(best_weights_path),
        "onnx_path": str(onnx_path) if onnx_path else None,
    }

    # Save summary json
    summary_path = save_dir / "experiment_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(experiment_report, f, indent=2)

    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)
    print(f"Val mAP@50:      {val_map50 * 100:.1f}%")
    print(f"Val mAP@50-95:   {val_map * 100:.1f}%")
    print(f"Test mAP@50:     {test_map50 * 100:.1f}% (Unseen footage)")
    print(f"Test mAP@50-95:  {test_map * 100:.1f}%")
    print(f"Best Weights:    {best_weights_path}")
    print(f"ONNX Export:     {onnx_path}")
    print(f"Report JSON:     {summary_path}")
    print("=" * 60)

    return experiment_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLO entity detector with controlled experiments.")
    parser.add_argument("--model", default="yolov8n.pt", help="Base model checkpoint")
    parser.add_argument("--data", default="training/data.yaml", help="Path to data.yaml")
    parser.add_argument("--imgsz", type=int, default=960, help="Input image resolution")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", default=None, help="Device (cpu, cuda:0)")
    parser.add_argument("--project", default="dataset/runs/train", help="Run project directory")
    parser.add_argument("--name", default="yolov8n_smallobj_960", help="Experiment name")
    parser.add_argument("--no-onnx", action="store_true", help="Skip ONNX export")

    args = parser.parse_args()

    run_training_experiment(
        data_yaml=Path(args.data),
        model_name=args.model,
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch_size=args.batch,
        seed=args.seed,
        device=args.device,
        project_dir=Path(args.project),
        experiment_name=args.name,
        export_onnx=not args.no_onnx,
    )


if __name__ == "__main__":
    main()
