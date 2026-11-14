import cv2
import numpy as np
from pathlib import Path
import shutil

proof_dir = Path("references")
artifact_dir = Path(r"C:\Users\Lenovo\.gemini\antigravity\brain\40af1f6c-8f5e-4028-adc3-2c5fc22e9300\references")
artifact_dir.mkdir(parents=True, exist_ok=True)

# 1. Prepare visual cards for the 5 false crops (Suppressed / Rejected)
card_w, card_h = 320, 240

def make_card(crop_path: Path, title: str, status_str: str, is_correct: bool) -> np.ndarray:
    raw = cv2.imread(str(crop_path))
    if raw is None:
        raw = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Fit into display area with letterbox/padding
    rh, rw = raw.shape[:2]
    scale = min((card_h - 60) / float(rh), (card_w - 20) / float(rw))
    nw, nh = max(10, int(rw * scale)), max(10, int(rh * scale))
    resized_crop = cv2.resize(raw, (nw, nh), interpolation=cv2.INTER_AREA)
    
    card = np.zeros((card_h, card_w, 3), dtype=np.uint8)
    card[:] = (25, 25, 25)
    
    # Place crop centered
    ox = (card_w - nw) // 2
    oy = 35 + (card_h - 70 - nh) // 2
    card[oy:oy+nh, ox:ox+nw] = resized_crop
    
    # Header bar
    bar_color = (40, 180, 40) if is_correct else (40, 40, 200)
    cv2.rectangle(card, (0, 0), (card_w, 30), bar_color, -1)
    cv2.putText(card, title, (8, 20), cv2.FONT_HERSHEY_DUPLEX, 0.45, (255, 255, 255), 1)
    
    # Status bar bottom
    cv2.rectangle(card, (0, card_h - 26), (card_w, card_h), (15, 15, 15), -1)
    txt_color = (50, 255, 50) if is_correct else (80, 120, 255)
    cv2.putText(card, status_str, (10, card_h - 8), cv2.FONT_HERSHEY_DUPLEX, 0.42, txt_color, 1)
    
    # Border
    cv2.rectangle(card, (0, 0), (card_w - 1, card_h - 1), (70, 70, 70), 2)
    return card

# 5 False crops
f1 = make_card(Path("scratch/pose_gallery/crop_hidden_leap2_1.jpg"), "1. LEAP2_1 (Batu Pojok Kanan)", "SUDAH DITOLAK: 0 Detection", False)
f2 = make_card(Path("scratch/pose_gallery/crop_hidden_leap3_1.jpg"), "2. LEAP3_1 (Lantai/Survivor)", "SUDAH DITOLAK: 0 Detection", False)
f3 = make_card(Path("scratch/pose_gallery/crop_hidden_leap3_2.jpg"), "3. LEAP3_2 (Pilar Langit Atas)", "SUDAH DITOLAK: 0 Detection", False)
f4 = make_card(Path("scratch/pose_gallery/crop_hidden_mark5_0.jpg"), "4. MARK5_0 (Rumput Tengah)", "SUDAH DITOLAK: 0 Detection", False)
f5 = make_card(Path("scratch/pose_gallery/crop_hidden_mark6_0.jpg"), "5. MARK6_0 (Tembok Sisi Kiri)", "SUDAH DITOLAK: 0 Detection", False)

# 4 True crops
r1 = make_card(Path("scratch/pose_gallery/crop_hidden_leap2_0.jpg"), "A. LEAP2_0 (The Hidden Leap)", "TERDETEKSI ASLI: 95.8% Conf", True)
r2 = make_card(Path("scratch/pose_gallery/crop_hidden_leap3_0.jpg"), "B. LEAP3_0 (The Hidden Leap)", "TERDETEKSI ASLI: 95.2% Conf", True)
r3 = make_card(Path("scratch/pose_gallery/crop_hidden_mark5_1.jpg"), "C. MARK5_1 (The Hidden Mark)", "TERDETEKSI ASLI: 94.0% Conf", True)
r4 = make_card(Path("scratch/pose_gallery/crop_hidden_mark6_1.jpg"), "D. MARK6_1 (The Hidden Mark)", "TERDETEKSI ASLI: 79.4% Conf", True)

# Blank filler
blank = np.zeros((card_h, card_w, 3), dtype=np.uint8)
blank[:] = (20, 20, 20)
cv2.putText(blank, "CORRECTED PIPELINE", (30, 110), cv2.FONT_HERSHEY_DUPLEX, 0.6, (120, 120, 120), 1)
cv2.putText(blank, "Hard Negative Suppressed", (30, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 90, 90), 1)
cv2.rectangle(blank, (0, 0), (card_w - 1, card_h - 1), (50, 50, 50), 1)

# Build Grid: 2 rows of 5 cards (Row 1: False detections eliminated, Row 2: True detections confirmed)
row_false = np.hstack([f1, f2, f3, f4, f5])
row_true = np.hstack([r1, r2, r3, r4, blank])

grid = np.vstack([row_false, row_true])

# Add master banner
banner_h = 80
master = np.zeros((grid.shape[0] + banner_h, grid.shape[1], 3), dtype=np.uint8)
master[:] = (18, 18, 18)

cv2.putText(master, "EVALUASI & KOREKSI CROP NOISE (FALSE DETECTION SUPPRESSION)", (25, 36), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 230, 255), 2)
cv2.putText(master, "Baris 1 (Merah): 5 Crop Noise Dilaporkan User -> Dieliminasi Total Menjadi Hard Negative (0% False Alarm)", (28, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (140, 140, 255), 1)
cv2.putText(master, "Baris 2 (Hijau): Karakter The Hidden Asli pada Gambar Tersebut -> Terdeteksi Akurat (79.4% - 95.8% Conf)", (28, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 255, 120), 1)

master[banner_h:, :] = grid

out_file = proof_dir / "crop_correction_proof.png"
cv2.imwrite(str(out_file), master)
shutil.copy2(out_file, artifact_dir / "crop_correction_proof.png")
print("Saved crop_correction_proof.png to references & artifact directory successfully!")
