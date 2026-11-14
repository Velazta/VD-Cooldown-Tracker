import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import os
from detection.yolo_detector import YoloDetector

det = YoloDetector("models/the_hidden_yolov8n.onnx", confidence_threshold=0.30)

files = [
    "hidden_leap.png", "hidden_leap2.png", "hidden_leap3.png", "hidden_leap4.png",
    "hidden_mark.png", "hidden_mark2.png", "hidden_stay.png"
]
for f in files:
    p = f"database/dataset/HIDDEN/PNG/INGAME/{f}"
    img = cv2.imread(p)
    if img is not None:
        res = det.process_frame(img)
        print(f"{f}: {[(t.class_name, f'{t.confidence:.1%}', t.bbox) for t in res.targets]}")
