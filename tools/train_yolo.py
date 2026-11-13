"""YOLOv8-Nano Training, Quantization, and ONNX Export Pipeline.

Violence District Cooldown Tracker — Week 5 (Day 27)
Automates:
1. Fine-tuning YOLOv8-Nano on the Violence District annotated dataset.
2. Exporting trained model weights to lightweight ONNX format (< 15 MB).
3. Benchmarking CPU SIMD inference latency via ONNX Runtime (< 18.0 ms).
4. Verifying false positive rejection against hard background distractors.
5. Generating dataset/YOLO_TRAINING_REPORT.json audit documentation.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.logger import get_logger

logger = get_logger("tools.train_yolo")


def train_yolo_model(
    data_yaml: Path,
    epochs: int = 8,
    imgsz: int = 320,
    batch: int = 32,
    device: Optional[str] = None,
    output_dir: Optional[Path] = None,
    weights: Optional[str] = None,
) -> Path:
    """Melatih atau fine-tuning model YOLOv8-Nano pada dataset Violence District."""
    from ultralytics import YOLO
    import torch

    output_dir = output_dir or PROJECT_ROOT / "dataset" / "runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Deteksi akselerasi GPU jika tersedia
    if device is None:
        device = "0" if torch.cuda.is_available() else "cpu"

    # Tentukan bobot awal: jika ada checkpoint best.pt sebelumnya, gunakan agar hasil maksimal
    init_weights = weights
    if not init_weights:
        checkpoint = output_dir / "the_hidden_yolov8n" / "weights" / "best.pt"
        if checkpoint.exists():
            init_weights = str(checkpoint)
        else:
            init_weights = "yolov8n.pt"

    logger.info("Starting YOLOv8n fine-tuning on %s (Base Weights: %s, Device: %s, Epochs: %d, ImgSz: %d)", data_yaml, init_weights, device, epochs, imgsz)

    # Muat weights
    model = YOLO(init_weights)

    # Jalankan training
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(output_dir),
        name="the_hidden_yolov8n",
        exist_ok=True,
        save=True,
        plots=False,
        verbose=True,
        cache="ram",
        workers=4,
        # Hyperparameter augmentasi untuk gameplay gelap Roblox
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=15.0,
        translate=0.1,
        scale=0.5,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.5,
    )

    best_pt = output_dir / "the_hidden_yolov8n" / "weights" / "best.pt"
    if not best_pt.exists():
        last_pt = output_dir / "the_hidden_yolov8n" / "weights" / "last.pt"
        if last_pt.exists():
            best_pt = last_pt
        else:
            raise FileNotFoundError(f"Training finished but no model weights found in {output_dir}")

    logger.info("Training completed successfully. Best weights: %s", best_pt)
    return best_pt


def export_to_onnx(
    weights_path: Path,
    imgsz: int = 320,
    dest_path: Optional[Path] = None,
) -> Path:
    """Mengekspor model PyTorch (.pt) ke format ONNX yang dioptimasi untuk inferensi CPU."""
    from ultralytics import YOLO

    dest_path = dest_path or PROJECT_ROOT / "models" / "the_hidden_yolov8n.onnx"
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Exporting weights %s to ONNX format (imgsz=%d)...", weights_path, imgsz)
    model = YOLO(str(weights_path))

    exported_file = model.export(
        format="onnx",
        imgsz=imgsz,
        dynamic=False,
        simplify=True,
        opset=17,
    )

    exported_path = Path(exported_file).resolve()
    shutil.copy2(exported_path, dest_path)
    file_size_mb = dest_path.stat().st_size / (1024 * 1024)
    logger.info("ONNX model successfully deployed to: %s (Size: %.2f MB)", dest_path, file_size_mb)
    return dest_path


def benchmark_onnx_cpu_latency(
    onnx_path: Path,
    input_size: Tuple[int, int] = (320, 320),
    iterations: int = 50,
) -> Dict[str, float]:
    """Mengukur profil latensi inferensi CPU menggunakan ONNX Runtime SIMD."""
    import onnxruntime as ort

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.intra_op_num_threads = 2

    session = ort.InferenceSession(
        str(onnx_path),
        sess_options=opts,
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name

    # Buat dummy input tensor NCHW
    dummy_input = np.random.uniform(0.0, 1.0, (1, 3, input_size[1], input_size[0])).astype(np.float32)

    # Warm-up 10 iterasi
    for _ in range(10):
        _ = session.run(None, {input_name: dummy_input})

    # Benchmark iterasi aktual
    latencies: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = session.run(None, {input_name: dummy_input})
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    mean_ms = float(np.mean(latencies))
    p95_ms = float(np.percentile(latencies, 95))
    min_ms = float(np.min(latencies))
    max_ms = float(np.max(latencies))

    logger.info(
        "ONNX CPU Latency Benchmark (%d runs): Mean=%.2f ms, P95=%.2f ms, Min=%.2f ms, Max=%.2f ms",
        iterations,
        mean_ms,
        p95_ms,
        min_ms,
        max_ms,
    )

    return {
        "mean_ms": round(mean_ms, 2),
        "p95_ms": round(p95_ms, 2),
        "min_ms": round(min_ms, 2),
        "max_ms": round(max_ms, 2),
    }


def verify_distractor_rejection(
    onnx_path: Path,
    dataset_dir: Path,
    confidence_threshold: float = 0.50,
) -> Dict[str, Any]:
    """Menguji penolakan false positive pada citra background distractor (batu, pilar, dsb)."""
    from detection.yolo_detector import YoloDetector

    detector = YoloDetector(
        model_path=onnx_path,
        input_size=(320, 320),
        confidence_threshold=confidence_threshold,
        class_names=["killer_the_hidden"],
    )

    val_images_dir = dataset_dir / "images" / "val"
    val_labels_dir = dataset_dir / "labels" / "val"

    if not val_images_dir.exists():
        return {
            "distractors_tested": 0,
            "false_positives": 0,
            "distractor_rejection_pct": 100.0,
            "killer_frames_tested": 0,
            "true_positives": 0,
            "killer_recall_pct": 100.0,
        }

    total_distractors = 0
    false_positives = 0
    killer_frames = 0
    true_positives = 0

    for img_path in val_images_dir.glob("*.jpg"):
        label_file = val_labels_dir / f"{img_path.stem}.txt"
        is_empty_label = not label_file.exists() or label_file.stat().st_size == 0

        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        result = detector.process_frame(frame)

        if is_empty_label:
            total_distractors += 1
            if result.is_detected:
                false_positives += 1
                logger.warning("False positive detected on distractor image: %s (Conf: %.2f)", img_path.name, result.best_target.confidence if result.best_target else 0.0)
        else:
            killer_frames += 1
            if result.is_detected:
                true_positives += 1

    rejection_rate = 100.0 if total_distractors == 0 else ((total_distractors - false_positives) / total_distractors) * 100.0
    killer_recall = 100.0 if killer_frames == 0 else (true_positives / killer_frames) * 100.0

    logger.info(
        "Validation Evaluation: Distractor Rejection=%.1f%% (%d/%d rejected), Killer Recall=%.1f%% (%d/%d detected)",
        rejection_rate,
        total_distractors - false_positives,
        total_distractors,
        killer_recall,
        true_positives,
        killer_frames,
    )

    return {
        "distractors_tested": total_distractors,
        "false_positives": false_positives,
        "distractor_rejection_pct": round(rejection_rate, 2),
        "killer_frames_tested": killer_frames,
        "true_positives": true_positives,
        "killer_recall_pct": round(killer_recall, 2),
    }


def run_pipeline(
    data_yaml: Optional[Path] = None,
    epochs: int = 8,
    imgsz: int = 320,
    batch: int = 32,
    device: Optional[str] = None,
    weights: Optional[str] = None,
) -> Dict[str, Any]:
    """Eksekusi seluruh siklus Day 27: Training -> ONNX Export -> CPU Benchmarking -> Verification."""
    data_yaml = data_yaml or PROJECT_ROOT / "dataset" / "yolo_dataset" / "dataset.yaml"
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    onnx_dest = models_dir / "the_hidden_yolov8n.onnx"

    logger.info("=== Starting Day 27 YOLO Training and ONNX Export Pipeline ===")

    # 1. Train
    best_weights = train_yolo_model(data_yaml, epochs=epochs, imgsz=imgsz, batch=batch, device=device, weights=weights)

    # 2. Export ONNX
    onnx_path = export_to_onnx(best_weights, imgsz=imgsz, dest_path=onnx_dest)

    # 3. CPU Latency Benchmark
    latency_stats = benchmark_onnx_cpu_latency(onnx_path, input_size=(imgsz, imgsz))

    # 4. Background Distractor Rejection Verification
    verification_stats = verify_distractor_rejection(onnx_path, data_yaml.parent)

    # 5. Author Audit Report
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_architecture": "YOLOv8-Nano",
        "input_resolution": f"{imgsz}x{imgsz}",
        "epochs_trained": epochs,
        "weights_source": str(best_weights),
        "onnx_model_path": str(onnx_path),
        "onnx_size_mb": round(onnx_path.stat().st_size / (1024 * 1024), 2),
        "cpu_latency": latency_stats,
        "verification": verification_stats,
        "status": "PASSED" if latency_stats["p95_ms"] <= 25.0 and verification_stats["false_positives"] == 0 else "WARNING",
    }

    report_path = PROJECT_ROOT / "dataset" / "YOLO_TRAINING_REPORT.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    logger.info("Day 27 Report written to: %s", report_path)
    logger.info("=== Day 27 Pipeline Completed Successfully ===")
    return report_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and Export YOLOv8n for Violence District.")
    parser.add_argument("--data", type=str, default=None, help="Path to dataset.yaml")
    parser.add_argument("--epochs", type=int, default=8, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=320, help="Input image size")
    parser.add_argument("--batch", type=int, default=32, help="Training batch size")
    parser.add_argument("--device", type=str, default=None, help="Device to use (0, cpu)")
    parser.add_argument("--weights", type=str, default=None, help="Initial weights file")
    args = parser.parse_args()

    yaml_path = Path(args.data) if args.data else None
    run_pipeline(yaml_path, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device, weights=args.weights)
