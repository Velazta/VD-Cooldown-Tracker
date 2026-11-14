import cv2
import numpy as np
from pathlib import Path

crops_to_find = [
    ("crop_hidden_leap2_1.jpg", "hidden_leap2.png"),
    ("crop_hidden_leap3_1.jpg", "hidden_leap3.png"),
    ("crop_hidden_leap3_2.jpg", "hidden_leap3.png"),
    ("crop_hidden_mark5_0.jpg", "hidden_mark5.png"),
    ("crop_hidden_mark6_0.jpg", "hidden_mark6.png"),
]

for crop_name, img_name in crops_to_find:
    crop = cv2.imread(f"scratch/pose_gallery/{crop_name}")
    full = cv2.imread(f"database/dataset/HIDDEN/PNG/INGAME/{img_name}")
    
    # Template match to get exact coordinate in full image
    res = cv2.matchTemplate(full, crop, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    h, w = crop.shape[:2]
    
    print(f"=== {crop_name} in {img_name} ===")
    print(f"  Match Score: {max_val:.4f}")
    print(f"  Location (x, y, w, h): ({max_loc[0]}, {max_loc[1]}, {w}, {h})")
