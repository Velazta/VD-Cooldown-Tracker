"""Run multi-class YOLOv8n fine-tuning, export to ONNX, and benchmark."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.train_yolo import train_yolo_model, export_to_onnx, benchmark_onnx_cpu_latency

yaml_p = Path("dataset/multiclass_yolo/dataset.yaml")
base_weights = "dataset/runs/the_hidden_yolov8n/weights/best.pt"

print("Starting 6-epoch fine-tuning on multi-class Roblox dataset...")
best_pt = train_yolo_model(
    data_yaml=yaml_p,
    epochs=6,
    imgsz=320,
    batch=32,
    device="cpu",
    weights=base_weights,
)
print("Training completed. Best weights:", best_pt)

print("Exporting model to ONNX...")
onnx_dest = Path("models/the_hidden_yolov8n.onnx")
export_to_onnx(best_pt, imgsz=320, dest_path=onnx_dest)
print("Exported to:", onnx_dest)

print("Benchmarking ONNX CPU latency...")
bench = benchmark_onnx_cpu_latency(onnx_dest, iterations=30)
print("Benchmark result:", bench)
