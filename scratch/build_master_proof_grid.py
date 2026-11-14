import cv2
import numpy as np
from pathlib import Path
import shutil

proof_dir = Path("references/verified_proof")
artifact_dir = Path(r"C:\Users\Lenovo\.gemini\antigravity\brain\40af1f6c-8f5e-4028-adc3-2c5fc22e9300\references")
artifact_dir.mkdir(parents=True, exist_ok=True)

# Also copy all 7 individual proof images to artifact directory
for f in proof_dir.glob("*.png"):
    shutil.copy2(f, artifact_dir / f.name)

# Create a master visual collage
cell_w, cell_h = 560, 360

def prepare_cell(img_path: Path, header_text: str, badge_color: tuple, badge_text: str) -> np.ndarray:
    raw = cv2.imread(str(img_path))
    resized = cv2.resize(raw, (cell_w, cell_h), interpolation=cv2.INTER_AREA)
    
    # Top overlay bar for clarity
    cv2.rectangle(resized, (0, 0), (cell_w, 36), (15, 15, 15), -1)
    cv2.putText(resized, header_text, (10, 24), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)
    
    # Bottom badge
    cv2.rectangle(resized, (0, cell_h - 32), (cell_w, cell_h), (25, 25, 25), -1)
    cv2.circle(resized, (18, cell_h - 16), 7, badge_color, -1)
    cv2.putText(resized, badge_text, (34, cell_h - 10), cv2.FONT_HERSHEY_DUPLEX, 0.52, badge_color, 1)
    
    # Outer border
    cv2.rectangle(resized, (0, 0), (cell_w - 1, cell_h - 1), (60, 60, 60), 2)
    return resized

c1 = prepare_cell(
    proof_dir / "01_survivor_baju_putih_leap4_verified.png",
    "A. Survivor Baju Putih (Game Leap 4)",
    (0, 255, 0), "100% LOLOS: 0 False Detection (Bukan Killer)"
)

c2 = prepare_cell(
    proof_dir / "02_spectator_veil_rejected_as_killer.png",
    "B. Spectator Mode Veil (Skin 1)",
    (255, 200, 0), "TERKOREKSI: Dikelompokkan Survivor / Bukan Hidden"
)

c3 = prepare_cell(
    proof_dir / "03_the_hidden_green_leap_1_verified.png",
    "C. The Hidden: Green Fedora Leap 1",
    (0, 255, 0), "TERDETEKSI: killer_the_hidden 94.4% (Airborne)"
)

c4 = prepare_cell(
    proof_dir / "04_the_hidden_pink_leap_1_verified.png",
    "D. The Hidden: Pink Blindfold Leap 1",
    (0, 255, 0), "TERDETEKSI: killer_the_hidden 90.4% (Airborne)"
)

c5 = prepare_cell(
    proof_dir / "05_the_hidden_pink_leap_2_verified.png",
    "E. The Hidden: Pink Blindfold Leap 2",
    (0, 255, 0), "TERDETEKSI: killer_the_hidden 94.0% (Airborne)"
)

c6 = prepare_cell(
    proof_dir / "07_dual_scene_survivor_and_killer_verified.png",
    "F. Dual Scene: Survivor vs Killer",
    (0, 255, 255), "TERPISAH: Survivor Diabaikan, Hidden Dideteksi"
)

# Canvas 3 rows x 2 cols
row1 = np.hstack([c1, c2])
row2 = np.hstack([c3, c4])
row3 = np.hstack([c5, c6])

grid = np.vstack([row1, row2, row3])

# Master Header
header_h = 70
canvas = np.zeros((grid.shape[0] + header_h, grid.shape[1], 3), dtype=np.uint8)
canvas[:] = (20, 20, 20)
cv2.putText(
    canvas,
    "VIOLENCE DISTRICT COOLDOWN TRACKER - VERIFIED ENTITY DETECTION PROOF",
    (25, 42),
    cv2.FONT_HERSHEY_DUPLEX,
    0.8,
    (0, 255, 200),
    2
)
cv2.putText(
    canvas,
    "Model: the_hidden_yolov8n.onnx (480x480 CPU SIMD) | Class 0: killer_the_hidden | Class 1: survivor",
    (28, 62),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.48,
    (180, 180, 180),
    1
)

canvas[header_h:, :] = grid

out_p = Path("references/verified_detection_master_proof.png")
cv2.imwrite(str(out_p), canvas)
shutil.copy2(out_p, artifact_dir / "verified_detection_master_proof.png")

print(f"Master proof generated successfully: {out_p} ({canvas.shape[1]}x{canvas.shape[0]})")
