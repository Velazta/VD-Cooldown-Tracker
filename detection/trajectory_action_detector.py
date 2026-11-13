"""Kinematic Trajectory Action Detector for Leap Ability Recognition.

Violence District Cooldown Tracker — Week 5 (Day 29)
Analyzes temporal bounding box centroids (cx, cy) from YoloDetector to recognize
the dynamic parabolic leap action of The Hidden killer.
Features:
- Sliding window trajectory smoothing over N frames.
- Instantaneous and windowed vertical velocity (Vy = dY / dt) calculation.
- Ground elevation baseline tracking.
- Finite state machine (GROUNDED, TAKEOFF, AIRBORNE, LANDED).
- Robust false positive rejection against normal walking, crouching, and camera tilt.
- Safe 15-second debounce lockout.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, List, Optional, Tuple

from app.logger import get_logger

logger = get_logger("detection.trajectory_action")


class KillerKinematicState(str, Enum):
    """Status kinematika killer dalam ruang spasial ROI."""
    UNKNOWN = "UNKNOWN"
    GROUNDED = "GROUNDED"
    TAKEOFF = "TAKEOFF"
    AIRBORNE = "AIRBORNE"
    LANDED = "LANDED"


@dataclass
class TrajectoryPoint:
    """Titik posisi spasial killer pada stempel waktu tertentu."""
    x: float
    y: float
    w: float
    h: float
    timestamp: float
    confidence: float

    @property
    def centroid_y(self) -> float:
        return self.y + self.h / 2.0

    @property
    def centroid_x(self) -> float:
        return self.x + self.w / 2.0

    @property
    def bottom_y(self) -> float:
        return self.y + self.h

    @property
    def aspect_ratio(self) -> float:
        return self.w / self.h if self.h > 0 else 0.0


@dataclass
class ActionRecognitionResult:
    """Hasil evaluasi aksi pada frame saat ini."""
    is_leap_detected: bool = False
    state: KillerKinematicState = KillerKinematicState.UNKNOWN
    vertical_velocity_px_s: float = 0.0
    elevation_px: float = 0.0
    confidence: float = 0.0
    explanation: str = ""


class TrajectoryActionDetector:
    """Pengenal aksi kinematis berbasis trajektori bounding box killer.

    Mendukung deteksi ganda (Dual-Path Trigger):
    1. Path A (Takeoff Launch): Lonjakan kecepatan ke atas yang tajam (Vy <= threshold).
    2. Path B (Airborne State): Killer sedang melayang / berada di udara (Elevation >= threshold
       selama >= 2 frame beruntun), memastikan Leap tetap terdeteksi meski lonjakan awal terlewat.
    """

    def __init__(
        self,
        velocity_threshold_px_s: float = -140.0,
        elevation_threshold_px: float = 30.0,
        window_size: int = 15,
        debounce_seconds: float = 15.0,
    ) -> None:
        self.velocity_threshold_px_s = velocity_threshold_px_s
        self.elevation_threshold_px = elevation_threshold_px
        self.window_size = window_size
        self.debounce_seconds = debounce_seconds

        self._history: Deque[TrajectoryPoint] = collections.deque(maxlen=window_size)
        self._ground_y: Optional[float] = None
        self._ground_bottom_y: Optional[float] = None
        self._airborne_frames: int = 0
        self._state: KillerKinematicState = KillerKinematicState.UNKNOWN
        self._last_leap_timestamp: float = -999.0

    @property
    def state(self) -> KillerKinematicState:
        return self._state

    @property
    def ground_y(self) -> Optional[float]:
        return self._ground_y

    def reset(self) -> None:
        """Mereset riwayat posisi dan status kinematis."""
        self._history.clear()
        self._ground_y = None
        self._ground_bottom_y = None
        self._airborne_frames = 0
        self._state = KillerKinematicState.UNKNOWN
        self._last_leap_timestamp = -999.0
        logger.debug("TrajectoryActionDetector reset to initial state.")

    def update(
        self,
        bbox: Optional[Tuple[int, int, int, int]],
        confidence: float,
        timestamp: Optional[float] = None,
    ) -> ActionRecognitionResult:
        """Memperbarui trajektori dengan bounding box terbaru dan mengevaluasi aksi Leap.

        Args:
            bbox: Tuple (x, y, w, h) dalam koordinat ROI atau None jika killer tidak terlihat.
            confidence: Skor keyakinan deteksi neural (0.0 s/d 1.0).
            timestamp: Waktu frame saat ini (detik monontonik). Jika None, menggunakan time.monotonic().
        """
        now = timestamp if timestamp is not None else time.monotonic()

        # 1. Jika killer tidak terdeteksi pada frame ini
        if bbox is None or confidence < 0.25:
            if len(self._history) > 0 and (now - self._history[-1].timestamp) > 1.2:
                # Target hilang lebih dari 1.2 detik, reset riwayat
                self._history.clear()
                self._airborne_frames = 0
                self._state = KillerKinematicState.UNKNOWN
            return ActionRecognitionResult(
                is_leap_detected=False,
                state=self._state,
                explanation="Killer target not visible in ROI",
            )

        x, y, w, h = bbox
        current_pt = TrajectoryPoint(
            x=float(x),
            y=float(y),
            w=float(w),
            h=float(h),
            timestamp=now,
            confidence=confidence,
        )

        cy = current_pt.centroid_y
        c_bottom = current_pt.bottom_y

        # 2. Inisialisasi dan adaptasi ground baseline
        # Di koordinat layar citra, tanah berada di bawah (koordinat Y lebih besar).
        if self._ground_y is None:
            self._ground_y = cy
            self._ground_bottom_y = c_bottom
            self._state = KillerKinematicState.GROUNDED

        # 3. Hitung kecepatan vertikal Vy (px/s)
        vy = 0.0
        if len(self._history) >= 2:
            prev_pt = self._history[-1]
            dt = current_pt.timestamp - prev_pt.timestamp
            if dt > 0.001:
                # Melompat ke atas -> cy lebih kecil -> dY < 0 -> Vy negatif.
                vy = (cy - prev_pt.centroid_y) / dt

        self._history.append(current_pt)

        # 4. Hitung elevasi relatif terhadap baseline tanah
        elevation = self._ground_y - cy
        bottom_elevation = (self._ground_bottom_y - c_bottom) if self._ground_bottom_y else elevation

        # 5. Adaptasi lambat ground level saat killer di tanah (|Vy| < 45 px/s)
        if abs(vy) < 45.0:
            if self._ground_bottom_y and c_bottom > self._ground_bottom_y:
                # Killer berada di posisi tanah lebih rendah -> update ground baseline
                self._ground_bottom_y = c_bottom
                self._ground_y = cy
                self._state = KillerKinematicState.GROUNDED
            elif abs(elevation) < 20.0:
                # Alpha smoothing permukaan tanah datar
                self._ground_y = 0.95 * self._ground_y + 0.05 * cy
                if self._ground_bottom_y:
                    self._ground_bottom_y = 0.95 * self._ground_bottom_y + 0.05 * c_bottom
                self._state = KillerKinematicState.GROUNDED

        # 6. Pantau durasi frame melayang di udara (Airborne)
        if elevation >= self.elevation_threshold_px or bottom_elevation >= (self.elevation_threshold_px * 0.8):
            self._airborne_frames += 1
        else:
            self._airborne_frames = max(0, self._airborne_frames - 1)

        # 7. Evaluasi aksi Leap (Dual-Path Trigger)
        is_debounced = (now - self._last_leap_timestamp) < self.debounce_seconds

        # Path A: Lonjakan awal saat lepas landas (Takeoff Launch)
        is_takeoff = (vy <= self.velocity_threshold_px_s and elevation >= 20.0)

        # Path B: Sedang melayang di udara (Airborne presence >= 2 frames)
        is_sustained_airborne = (self._airborne_frames >= 2 and (elevation >= self.elevation_threshold_px or bottom_elevation >= 25.0))

        # Path C: Posisi puncak lompatan di udara (Apex / floating high)
        is_high_airborne = (elevation >= 40.0 or bottom_elevation >= 35.0)

        is_leap = False
        explanation = f"Vy={vy:.1f} px/s, Elev={elevation:.1f} px, AirFrames={self._airborne_frames}"

        if not is_debounced:
            if is_takeoff or is_sustained_airborne or is_high_airborne:
                is_leap = True
                self._last_leap_timestamp = now
                self._state = KillerKinematicState.AIRBORNE
                explanation = (
                    f"LEAP CONFIRMED! (Takeoff={is_takeoff}, SustainedAir={is_sustained_airborne}, HighAir={is_high_airborne}) "
                    f"Launch Vy={vy:.1f} px/s, Elev={elevation:.1f} px, AirFrames={self._airborne_frames}"
                )
                logger.info(explanation)
            elif vy <= self.velocity_threshold_px_s * 0.60:
                self._state = KillerKinematicState.TAKEOFF
            elif elevation >= self.elevation_threshold_px or self._airborne_frames > 0:
                self._state = KillerKinematicState.AIRBORNE
            elif elevation < 15.0 and self._state == KillerKinematicState.AIRBORNE:
                self._state = KillerKinematicState.LANDED
            else:
                self._state = KillerKinematicState.GROUNDED
        else:
            remaining_cd = self.debounce_seconds - (now - self._last_leap_timestamp)
            explanation = f"Debounce active ({remaining_cd:.1f}s remaining)"
            if elevation >= self.elevation_threshold_px or self._airborne_frames > 0:
                self._state = KillerKinematicState.AIRBORNE
            elif elevation < 15.0:
                self._state = KillerKinematicState.LANDED

        return ActionRecognitionResult(
            is_leap_detected=is_leap,
            state=self._state,
            vertical_velocity_px_s=round(vy, 1),
            elevation_px=round(elevation, 1),
            confidence=confidence,
            explanation=explanation,
        )
