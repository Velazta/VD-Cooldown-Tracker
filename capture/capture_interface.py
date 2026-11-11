"""
Abstract Capture Interface & Data Structures
Violence District Cooldown Tracker
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import numpy as np


class CaptureStatus(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    TARGET_LOST = "TARGET_LOST"
    ERROR = "ERROR"


@dataclass
class CapturedFrame:
    """Metadata lengkap untuk setiap frame yang berhasil diambil."""
    image: np.ndarray             # OpenCV BGR image array
    timestamp: float              # Monotonic timestamp (seconds)
    frame_index: int              # Nomor urut frame
    width: int                    # Lebar pixel frame
    height: int                   # Tinggi pixel frame
    latency_ms: float             # Waktu yang dihabiskan untuk menangkap frame ini (ms)


class BaseCaptureEngine(ABC):
    """Antarmuka dasar untuk semua backend screen capture."""

    @abstractmethod
    def start(self, target_title: str = "Roblox", target_fps: int = 30) -> bool:
        """Memulai proses capture di thread terpisah."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Menghentikan thread capture dengan aman (clean shutdown)."""
        pass

    @abstractmethod
    def get_latest_frame(self) -> Optional[CapturedFrame]:
        """Mengambil frame terbaru dari buffer."""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Status apakah engine sedang aktif berjalan."""
        pass

    @property
    @abstractmethod
    def status(self) -> CaptureStatus:
        """Status kondisi capture saat ini."""
        pass

    @property
    @abstractmethod
    def current_fps(self) -> float:
        """FPS capture riil terukur."""
        pass

    @property
    @abstractmethod
    def current_latency_ms(self) -> float:
        """Latensi rata-rata per frame (ms)."""
        pass
