"""
ROI (Region of Interest) Processor & Data Model
Violence District Cooldown Tracker
"""
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Dict, Any
import numpy as np
import cv2


@dataclass
class ROIConfig:
    """Model data koordinat area Region of Interest (HUD/Skill)."""
    x: int = 0
    y: int = 0
    width: int = 100
    height: int = 100
    enabled: bool = True

    def validate(self, frame_width: int, frame_height: int) -> bool:
        """Memeriksa apakah koordinat valid berada di dalam batas frame."""
        if not self.enabled:
            return False
        if self.width <= 0 or self.height <= 0:
            return False
        if self.x < 0 or self.y < 0:
            return False
        if self.x + self.width > frame_width or self.y + self.height > frame_height:
            return False
        return True

    def get_clamped_bounds(self, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
        """
        Mengamankan koordinat agar tidak pernah melampaui ukuran frame
        (mencegah IndexError atau slice array kosong saat window di-resize).
        """
        clamped_x = max(0, min(self.x, frame_width - 1))
        clamped_y = max(0, min(self.y, frame_height - 1))
        clamped_w = max(1, min(self.width, frame_width - clamped_x))
        clamped_h = max(1, min(self.height, frame_height - clamped_y))
        return clamped_x, clamped_y, clamped_w, clamped_h

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ROIConfig":
        return cls(
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 100)),
            height=int(data.get("height", 100)),
            enabled=bool(data.get("enabled", True))
        )


class ROIProcessor:
    """Modul eksekusi pemotongan ROI dan visualisasi bounding box."""

    def __init__(self, config: Optional[ROIConfig] = None):
        self.config = config or ROIConfig()

    def update_config(self, config: ROIConfig) -> None:
        self.config = config

    def crop(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Memotong area ROI dari frame sumber.
        Mengembalikan None jika frame tidak valid atau ROI dinonaktifkan.
        """
        if frame is None or frame.size == 0 or not self.config.enabled:
            return None

        h, w = frame.shape[:2]
        cx, cy, cw, ch = self.config.get_clamped_bounds(w, h)

        cropped = frame[cy:cy + ch, cx:cx + cw]
        if cropped.size == 0:
            return None

        return cropped

    def draw_roi_box(self, frame: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
        """
        Menggambar kotak batas ROI pada frame untuk kebutuhan kalibrasi di GUI.
        """
        if frame is None or frame.size == 0 or not self.config.enabled:
            return frame

        annotated = frame.copy()
        h, w = frame.shape[:2]
        cx, cy, cw, ch = self.config.get_clamped_bounds(w, h)

        # Gambar kotak ROI
        cv2.rectangle(annotated, (cx, cy), (cx + cw, cy + ch), color, thickness)
        # Label teks koordinat di atas kotak
        label = f"ROI: {cw}x{ch} @ ({cx},{cy})"
        cv2.putText(
            annotated,
            label,
            (cx, max(15, cy - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA
        )
        return annotated
