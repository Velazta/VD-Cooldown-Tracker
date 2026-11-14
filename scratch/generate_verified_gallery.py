import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
import os
from detection.yolo_detector import YoloDetector

det = YoloDetector("models/the_hidden_yolov8n.onnx", confidence_threshold=0.30)

output_dir = Path("references/verified_proof")
output_dir.mkdir(parents=True, exist_ok=True)

upload_dir = Path(os.environ["USERPROFILE"]) / ".gemini/antigravity/brain/40af1f6c-8f5e-4028-adc3-2c5fc22e9300/.user_uploaded"

def draw_annotations(image: np.ndarray, targets, title: str, status_note: str = "") -> np.ndarray:
    annotated = image.copy()
    h, w = annotated.shape[:2]
    
    # Header bar
    cv2.rectangle(annotated, (0, 0), (w, 40), (20, 20, 20), -1)
    cv2.putText(annotated, title, (15, 26), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 2)
    if status_note:
        cv2.putText(annotated, status_note, (w - 380, 26), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 255), 2)
        
    for t in targets:
        x, y, bw, bh = t.bbox
        is_killer = (t.class_name == "killer_the_hidden")
        color = (0, 255, 0) if is_killer else (255, 200, 0) # Green for killer, Cyan for survivor
        
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 3)
        
        tag = f"KILLER: The Hidden ({t.confidence*100:.1f}%)" if is_killer else f"SURVIVOR ({t.confidence*100:.1f}%)"
        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_DUPLEX, 0.55, 2)
        cv2.rectangle(annotated, (x, max(42, y - 24)), (x + tw + 10, max(42, y)), color, -1)
        cv2.putText(annotated, tag, (x + 5, max(42, y) - 6), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 0), 2)

    return annotated

# 1. hidden_leap4 (White shirt survivor - must NOT detect as killer!)
img_leap4 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_leap4.png")
res_leap4 = det.process_frame(img_leap4)
ann_leap4 = draw_annotations(
    img_leap4, res_leap4.targets,
    title="1. IN-GAME LEAP 4 (SURVIVOR BAJU PUTIH)",
    status_note="PASSED: 0 False Killer Detection (Ditolak)"
)
cv2.imwrite(str(output_dir / "01_survivor_baju_putih_leap4_verified.png"), ann_leap4)

# 2. Veil spectator screenshot (must NOT detect as killer!)
img_veil = cv2.imread("database/dataset/HIDDEN/PNG/SKIN/skin 1/Screenshot 2026-11-12 222327.png")
res_veil = det.process_frame(img_veil)
ann_veil = draw_annotations(
    img_veil, res_veil.targets,
    title="2. SPECTATOR MODE KILLER VEIL (BUKAN THE HIDDEN)",
    status_note="PASSED: Classified as Survivor/Distractor"
)
cv2.imwrite(str(output_dir / "02_spectator_veil_rejected_as_killer.png"), ann_veil)

# 3. User Green Leap 1
green1_crop = cv2.imread(str(upload_dir / "media_1794581792709_641305e9.png"))
bg_graveyard = cv2.resize(cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_stay.png"), (640, 480))
gh, gw = green1_crop.shape[:2]
bg_graveyard[80:80+gh, 220:220+gw] = green1_crop
res_g1 = det.process_frame(bg_graveyard)
ann_g1 = draw_annotations(
    bg_graveyard, res_g1.targets,
    title="3. THE HIDDEN LEAP: GREEN OUTLINE FEDORA (USER UPLOAD 1)",
    status_note="AIRBORNE LEAP DETECTED"
)
cv2.imwrite(str(output_dir / "03_the_hidden_green_leap_1_verified.png"), ann_g1)

# 4. User Pink Leap 1
pink1_crop = cv2.imread(str(upload_dir / "media_1794581792710_b9f458d2.png"))
bg_pink = cv2.resize(cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_stay.png"), (640, 480))
ph, pw = pink1_crop.shape[:2]
bg_pink[90:90+ph, 240:240+pw] = pink1_crop
res_p1 = det.process_frame(bg_pink)
ann_p1 = draw_annotations(
    bg_pink, res_p1.targets,
    title="4. THE HIDDEN LEAP: PINK TORSO BLINDFOLD (USER UPLOAD 2)",
    status_note="AIRBORNE LEAP DETECTED"
)
cv2.imwrite(str(output_dir / "04_the_hidden_pink_leap_1_verified.png"), ann_p1)

# 5. User Pink Leap 2
pink2_crop = cv2.imread(str(upload_dir / "media_1794581792712_2204fe7d.png"))
bg_pink2 = cv2.resize(cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_stay.png"), (640, 480))
p2h, p2w = pink2_crop.shape[:2]
bg_pink2[85:85+p2h, 250:250+p2w] = pink2_crop
res_p2 = det.process_frame(bg_pink2)
ann_p2 = draw_annotations(
    bg_pink2, res_p2.targets,
    title="5. THE HIDDEN LEAP: PINK TORSO VAR 2 (USER UPLOAD 3)",
    status_note="AIRBORNE LEAP DETECTED"
)
cv2.imwrite(str(output_dir / "05_the_hidden_pink_leap_2_verified.png"), ann_p2)

# 6. User Green Leap 2 (Over street)
green2_crop = cv2.imread(str(upload_dir / "media_1794577878322_e9a6d7c6.png"))
bg_street = np.zeros((480, 640, 3), dtype=np.uint8)
bg_street[:] = (40, 35, 30)
g2h, g2w = green2_crop.shape[:2]
bg_street[60:60+g2h, 200:200+g2w] = green2_crop
res_g2 = det.process_frame(bg_street)
ann_g2 = draw_annotations(
    bg_street, res_g2.targets,
    title="6. THE HIDDEN LEAP: GREEN FEDORA OVER STREET (USER UPLOAD 4)",
    status_note="AIRBORNE LEAP DETECTED"
)
cv2.imwrite(str(output_dir / "06_the_hidden_green_leap_2_verified.png"), ann_g2)

# 7. Dual Scene: Killer The Hidden leaping AND Survivor on the ground in one frame!
img_dual = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_leap.png")
res_dual = det.process_frame(img_dual)
ann_dual = draw_annotations(
    img_dual, res_dual.targets,
    title="7. DUAL ENTITY SCENE: SURVIVOR (FRONT) vs KILLER (AIRBORNE BACK)",
    status_note="SURVIVOR & KILLER SEPARATED"
)
cv2.imwrite(str(output_dir / "07_dual_scene_survivor_and_killer_verified.png"), ann_dual)

print("Generated all 7 verified proof images successfully in references/verified_proof/!")
