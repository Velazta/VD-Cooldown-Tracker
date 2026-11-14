import cv2
import numpy as np
from pathlib import Path

# Let's inspect where The Hidden is in hidden_mark5.png and hidden_mark6.png
img_m5 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_mark5.png")
img_m6 = cv2.imread("database/dataset/HIDDEN/PNG/INGAME/hidden_mark6.png")

print("mark5 shape:", img_m5.shape)
print("mark6 shape:", img_m6.shape)

# Let's check crop_hidden_mark5_0 vs actual character
crop_m5_0 = cv2.imread("scratch/pose_gallery/crop_hidden_mark5_0.jpg")
print("crop_hidden_mark5_0 shape:", crop_m5_0.shape)

crop_m6_0 = cv2.imread("scratch/pose_gallery/crop_hidden_mark6_0.jpg")
print("crop_hidden_mark6_0 shape:", crop_m6_0.shape)
