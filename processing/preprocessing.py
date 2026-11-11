"""
OpenCV Image Preprocessor & Visual Filter Pipeline
Violence District Cooldown Tracker
"""
import time
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Optional
import cv2
import numpy as np


class PreprocessorMode(Enum):
    RAW = "raw"
    GRAYSCALE = "grayscale"
    CLAHE = "clahe"
    THRESHOLD = "threshold"
    CANNY = "canny"


@dataclass
class PreprocessingConfig:
    mode: PreprocessorMode = PreprocessorMode.RAW
    scale_factor: float = 1.0              # Skala resolusi (0.25 - 1.0) untuk optimasi kecepatan
    clahe_clip_limit: float = 2.0          # Kontras adaptif untuk map malam gelap
    clahe_grid_size: Tuple[int, int] = (8, 8)
    threshold_val: int = 128               # Batas biner untuk thresholding
    threshold_max: int = 255
    canny_low: int = 50                    # Ambang deteksi tepi Canny
    canny_high: int = 150


class ImagePreprocessor:
    """
    Pipeline pemrosesan citra OpenCV terukur.
    Menerapkan transformasi visual dan mencatat waktu proses secara presisi.
    """

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        self.config = config or PreprocessingConfig()
        self._clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=self.config.clahe_grid_size
        )

    def update_config(self, config: PreprocessingConfig) -> None:
        self.config = config
        self._clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=self.config.clahe_grid_size
        )

    def process(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Memproses frame gambar sesuai mode konfigurasi aktif.
        Mengembalikan: (processed_image, processing_time_ms)
        """
        if image is None or image.size == 0:
            return image, 0.0

        t0 = time.perf_counter()

        # 1. Opsional: Rescale ukuran jika scale_factor != 1.0
        frame = image
        if 0.1 <= self.config.scale_factor < 0.99:
            h, w = frame.shape[:2]
            target_w = max(10, int(w * self.config.scale_factor))
            target_h = max(10, int(h * self.config.scale_factor))
            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # 2. Pipeline Filter Sesuai Mode
        mode = self.config.mode

        if mode == PreprocessorMode.RAW:
            result = frame

        elif mode == PreprocessorMode.GRAYSCALE:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                result = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                result = frame

        elif mode == PreprocessorMode.CLAHE:
            # CLAHE: Menguatkan kontras lokal pada scene gelap (sangat cocok untuk Violence District)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                # Konversi ke LAB color space untuk hanya mencerahkan channel L (Luminance) tanpa merusak warna
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l_enhanced = self._clahe.apply(l)
                enhanced_lab = cv2.merge((l_enhanced, a, b))
                result = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            else:
                result = self._clahe.apply(frame)

        elif mode == PreprocessorMode.THRESHOLD:
            # Grayscale -> Gaussian Blur -> Binary Otsu Thresholding
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, result = cv2.threshold(
                blurred,
                self.config.threshold_val,
                self.config.threshold_max,
                cv2.THRESH_BINARY
            )

        elif mode == PreprocessorMode.CANNY:
            # Grayscale -> Gaussian Blur -> Canny Edge Detection
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            result = cv2.Canny(blurred, self.config.canny_low, self.config.canny_high)

        else:
            result = frame

        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0
        return result, elapsed_ms
