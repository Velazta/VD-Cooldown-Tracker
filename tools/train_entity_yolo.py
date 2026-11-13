"""Train 2-Class YOLOv8n (killer_the_hidden vs survivor) and Export to ONNX."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO
import torch

data_yaml = PROJECT_ROOT / "dataset" / "entity_yolo" / "dataset.yaml"
output_dir = PROJECT_ROOT / "dataset" / "runs"
output_dir.mkdir(parents=True, exist_ok=True)

print("Starting 2-Class Entity YOLOv8n training (killer_the_hidden vs survivor)...")
model = YOLO("yolov8n.pt")

results = model.train(
    data=str(data_yaml),
    epochs=6,
    imgsz=480,
    batch=16,
    device="cpu",
    project=str(output_dir),
    name="the_hidden_entity_yolov8n",
    exist_ok=True,
    save=True,
    cache="ram",
    workers=4,
    plots=True,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=15.0,
    translate=0.1,
    scale=0.5,
    fliplr=0.5,
    mosaic=0.5,
)

best_pt = output_dir / "the_hidden_entity_yolov8n" / "weights" / "best.pt"
print("Training completed. Best weights:", best_pt)

print("Exporting to ONNX format (imgsz=480)...")
dest_onnx = PROJECT_ROOT / "models" / "the_hidden_yolov8n.onnx"
dest_onnx.parent.mkdir(parents=True, exist_ok=True)

model_best = YOLO(str(best_pt))
exported = model_best.export(format="onnx", imgsz=480, simplify=True, opset=17)

import shutil
shutil.copy2(exported, dest_onnx)
print("ONNX model deployed to:", dest_onnx, f"({dest_onnx.stat().st_size / (1024*1024):.2f} MB)")
