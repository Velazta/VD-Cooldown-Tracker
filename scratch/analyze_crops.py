import cv2
import numpy as np
from pathlib import Path

# Load original full images
img_leap2 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_leap2.png")
img_leap3 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_leap3.png")
img_mark5 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_mark5.png")
img_mark6 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_mark6.png")

print("=== 1. crop_hidden_leap2_1 ===")
# Origin: hidden_leap2 bbox=(667, 3, 177, 241)
crop1 = img_leap2[3:3+241, 667:667+177]
print("leap2_1 region:", "x=667..844, y=3..244 (Pojok Kanan Atas)")
# What is here? Let's check dominant color and description:
print("Average BGR:", crop1.mean(axis=(0,1)))

print("\n=== 2. crop_hidden_leap3_1 ===")
# Origin: hidden_leap3 bbox=(276, 407, 577, 471)
crop2 = img_leap3[407:407+471, 276:276+577]
print("leap3_1 region:", "x=276..853, y=407..878 (Area Bawah/Lantai/Survivor)")
print("Average BGR:", crop2.mean(axis=(0,1)))

print("\n=== 3. crop_hidden_leap3_2 ===")
# Origin: hidden_leap3 bbox=(876, 0, 228, 319)
crop3 = img_leap3[0:319, 876:876+228]
print("leap3_2 region:", "x=876..1104, y=0..319 (Pojok Kanan Atas/Langit/Pilar)")
print("Average BGR:", crop3.mean(axis=(0,1)))

print("\n=== 4. crop_hidden_mark5_0 ===")
# Origin: hidden_mark5 bbox=(364, 341, 296, 156)
crop4 = img_mark5[341:341+156, 364:364+296]
print("mark5_0 region:", "x=364..660, y=341..497")
print("Average BGR:", crop4.mean(axis=(0,1)))

print("\n=== 5. crop_hidden_mark6_0 ===")
# Origin: hidden_mark6 bbox=(232, 280, 296, 185)
crop5 = img_mark6[280:280+185, 232:232+296]
print("mark6_0 region:", "x=232..528, y=280..465")
print("Average BGR:", crop5.mean(axis=(0,1)))
