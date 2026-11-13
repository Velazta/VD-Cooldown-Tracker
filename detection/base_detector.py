"""Base Detector Abstract Interface.

Violence District Cooldown Tracker — Week 5
Defines the standard contract for visual detectors (Template, Hybrid, and Neural YOLO).
Enables seamless, modular swapping of detection engines behind DetectionWorker.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import numpy as np

from detection.detection_result import DetectionResult


class BaseDetector(ABC):
    """Antarmuka dasar abstrak untuk modul deteksi visual."""

    @property
    @abstractmethod
    def confidence_threshold(self) -> float:
        """Mengambil ambang batas keyakinan deteksi aktif."""
        pass

    @confidence_threshold.setter
    @abstractmethod
    def confidence_threshold(self, value: float) -> None:
        """Menyetel ambang batas keyakinan deteksi."""
        pass

    @abstractmethod
    def process_frame(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
        **kwargs: Any,
    ) -> Any:
        """Mengevaluasi satu frame citra dan mengembalikan evaluasi deteksi terperinci.

        Args:
            frame: Matriks citra BGR input.
            frame_index: Nomor urut frame.
            timestamp: Waktu monotonic pengambilan frame.
            **kwargs: Parameter tambahan spesifik detektor (misal: audio_confirmed).

        Returns:
            Objek evaluasi deteksi (berisi skor, bounding box, latensi).
        """
        pass
