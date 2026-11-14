import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from detection.yolo_detector import YoloDetector

det = YoloDetector("models/the_hidden_yolov8n.onnx", confidence_threshold=0.35)

print("=== 1. TEST 5 CROP PALSU YANG DILAPORKAN USER ===")
fakes = [
    ("crop_hidden_leap2_1 (batu pojok kanan)", "scratch/pose_gallery/crop_hidden_leap2_1.jpg"),
    ("crop_hidden_leap3_1 (lantai/survivor)", "scratch/pose_gallery/crop_hidden_leap3_1.jpg"),
    ("crop_hidden_leap3_2 (pilar langit kanan)", "scratch/pose_gallery/crop_hidden_leap3_2.jpg"),
    ("crop_hidden_mark5_0 (rumput tanah kosong)", "scratch/pose_gallery/crop_hidden_mark5_0.jpg"),
    ("crop_hidden_mark6_0 (tembok pilar kiri)", "scratch/pose_gallery/crop_hidden_mark6_0.jpg"),
]

for label, p in fakes:
    crop = cv2.imread(p)
    ch, cw = crop.shape[:2]
    max_dim = max(ch, cw, 480)
    canvas = np.zeros((max_dim, max_dim, 3), dtype=np.uint8)
    canvas[:] = (35, 30, 25)
    canvas[0:ch, 0:cw] = crop
    res = det.process_frame(canvas)
    print(f"{label}:")
    print("  Detected count:", len(res.targets), [(t.class_name, f"{t.confidence:.1%}") for t in res.targets])

print("\n=== 2. TEST 4 CROP ASLI THE HIDDEN ===")
reals = [
    ("crop_hidden_leap2_0 (THE HIDDEN LEAP ASLI)", "scratch/pose_gallery/crop_hidden_leap2_0.jpg"),
    ("crop_hidden_leap3_0 (THE HIDDEN LEAP ASLI)", "scratch/pose_gallery/crop_hidden_leap3_0.jpg"),
    ("crop_hidden_mark5_1 (THE HIDDEN MARK ASLI)", "scratch/pose_gallery/crop_hidden_mark5_1.jpg"),
    ("crop_hidden_mark6_1 (THE HIDDEN MARK ASLI)", "scratch/pose_gallery/crop_hidden_mark6_1.jpg"),
]

for label, p in reals:
    crop = cv2.imread(p)
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    canvas[:] = (35, 30, 25)
    ch, cw = crop.shape[:2]
    canvas[100:100+ch, 200:200+cw] = crop
    res = det.process_frame(canvas)
    print(f"{label}:")
    print("  Detected count:", len(res.targets), [(t.class_name, f"{t.confidence:.1%}") for t in res.targets])

print("\n=== 3. TEST FULL IN-GAME IMAGES ===")
fulls = ["hidden_leap2.png", "hidden_leap3.png", "hidden_mark5.png", "hidden_mark6.png"]
for f in fulls:
    img = cv2.imread(f"database/dataset/HIDDEN/PNG/INGAME/{f}")
    res = det.process_frame(img)
    print(f"{f}: {len(res.targets)} targets -> {[(t.class_name, f'{t.confidence:.1%}', t.bbox) for t in res.targets]}")
