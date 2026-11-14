import cv2
import numpy as np
from pathlib import Path

# Let's inspect where The Hidden actually is in hidden_leap2, hidden_leap3, hidden_mark5, hidden_mark6
# We can do this by checking the other crops in scratch/pose_gallery or inspecting the images!

print("Crops in pose_gallery:")
for p in sorted(Path("scratch/pose_gallery").glob("*.jpg")):
    print(p.name)
