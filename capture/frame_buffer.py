"""
Thread-safe Latest Frame Buffer (Producer-Consumer Ring Buffer)
Violence District Cooldown Tracker
"""
import threading
from collections import deque
from typing import Optional, Dict
from capture.capture_interface import CapturedFrame


class LatestFrameBuffer:
    """
    Buffer ring thread-safe dengan strategi 'drop-oldest'.
    Menjamin processing selalu mendapatkan frame terbaru tanpa antrean frame usang (zero queue lag).
    """

    def __init__(self, maxsize: int = 1):
        self._maxsize = max(1, maxsize)
        self._buffer = deque(maxlen=self._maxsize)
        self._lock = threading.Lock()
        self._total_pushed = 0
        self._total_dropped = 0

    def push(self, frame: CapturedFrame) -> None:
        """Menyimpan frame baru ke buffer. Jika penuh, frame terlama otomatis dibuang."""
        with self._lock:
            if len(self._buffer) >= self._maxsize:
                self._total_dropped += 1
            self._buffer.append(frame)
            self._total_pushed += 1

    def get_latest(self) -> Optional[CapturedFrame]:
        """Mengambil frame terbaru tanpa menghapusnya (non-destructive peek/read)."""
        with self._lock:
            if self._buffer:
                return self._buffer[-1]
            return None

    def pop_latest(self) -> Optional[CapturedFrame]:
        """Mengambil frame terbaru dan membersihkan buffer (destructive read)."""
        with self._lock:
            if self._buffer:
                return self._buffer.pop()
            return None

    def clear(self) -> None:
        """Membersihkan seluruh isi buffer."""
        with self._lock:
            self._buffer.clear()

    @property
    def stats(self) -> Dict[str, int]:
        """Mengembalikan statistik throughput buffer."""
        with self._lock:
            return {
                "size": len(self._buffer),
                "total_pushed": self._total_pushed,
                "total_dropped": self._total_dropped,
            }
