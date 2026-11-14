import cv2
from pathlib import Path

crops_other = [
    ("crop_hidden_leap2_0.jpg", "hidden_leap2.png"),
    ("crop_hidden_leap3_0.jpg", "hidden_leap3.png"),
    ("crop_hidden_mark5_1.jpg", "hidden_mark5.png"),
    ("crop_hidden_mark6_1.jpg", "hidden_mark6.png"),
]

for crop_name, img_name in crops_other:
    p_crop = Path(f"scratch/pose_gallery/{crop_name}")
    if not p_crop.exists():
        print(f"{crop_name}: NOT FOUND")
        continue
    crop = cv2.imread(str(p_crop))
    full = cv2.imread(f"database/dataset/HIDDEN/PNG/INGAME/{img_name}")
    
    res = cv2.matchTemplate(full, crop, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    h, w = crop.shape[:2]
    print(f"=== {crop_name} in {img_name} ===")
    print(f"  Match Score: {max_val:.4f}")
    print(f"  Location (x, y, w, h): ({max_loc[0]}, {max_loc[1]}, {w}, {h})")
