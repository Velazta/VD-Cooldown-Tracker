import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

out_dir = Path("references/debug_crops_origin")
out_dir.mkdir(parents=True, exist_ok=True)

# The coordinates from step 3701:
# leap2: Target 0: (384, 147, 80, 91), Target 1: (667, 3, 177, 241)
# leap3: Target 0: (567, 91, 93, 112), Target 1: (276, 407, 577, 471), Target 2: (876, 0, 228, 319)
# mark5: Target 0: (364, 341, 296, 156)
# mark6: Target 0: (232, 280, 296, 185) or similar

targets_to_inspect = {
    "hidden_leap2.png": [
        ("crop_hidden_leap2_0 (The Hidden?)", (384, 147, 80, 91), (0, 255, 0)),
        ("crop_hidden_leap2_1 (SALAH DETECT)", (667, 3, 177, 241), (0, 0, 255)),
    ],
    "hidden_leap3.png": [
        ("crop_hidden_leap3_0 (The Hidden?)", (567, 91, 93, 112), (0, 255, 0)),
        ("crop_hidden_leap3_1 (SALAH DETECT)", (276, 407, 577, 471), (0, 0, 255)),
        ("crop_hidden_leap3_2 (SALAH DETECT)", (876, 0, 228, 319), (0, 0, 255)),
    ],
    "hidden_mark5.png": [
        ("crop_hidden_mark5_0 (SALAH DETECT)", (364, 341, 296, 156), (0, 0, 255)),
    ],
    "hidden_mark6.png": [
        ("crop_hidden_mark6_0 (SALAH DETECT)", (232, 280, 296, 185), (0, 0, 255)),
    ]
}

for img_name, boxes in targets_to_inspect.items():
    p = Path("database/dataset/HIDDEN/PNG/INGAME") / img_name
    img = cv2.imread(str(p))
    if img is None:
        print(f"Could not load {p}")
        continue
    ann = img.copy()
    for label, (x, y, w, h), color in boxes:
        cv2.rectangle(ann, (x, y), (x + w, y + h), color, 3)
        cv2.putText(ann, label, (x, max(25, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    out_p = out_dir / f"annotated_debug_{img_name}"
    cv2.imwrite(str(out_p), ann)
    print(f"Saved {out_p}")
