"""Unit tests for TrajectoryActionDetector (Day 29 Kinematic Action Recognition)."""

import time
import pytest
from detection.trajectory_action_detector import (
    ActionRecognitionResult,
    KillerKinematicState,
    TrajectoryActionDetector,
)


def test_trajectory_initialization():
    """Menguji inisialisasi awal detektor trajektori kinematis."""
    detector = TrajectoryActionDetector()
    assert detector.state == KillerKinematicState.UNKNOWN
    assert detector.ground_y is None


def test_grounded_walking_no_leap():
    """Menguji killer yang berjalan mendatar di tanah tidak memicu aksi Leap."""
    detector = TrajectoryActionDetector()
    t = 1000.0

    # Simulasi killer berjalan di koordinat Y=400, X bergeser dari 200 ke 300
    for i in range(10):
        t += 0.04  # 25 FPS
        res = detector.update(
            bbox=(200 + i * 10, 400, 60, 120),
            confidence=0.85,
            timestamp=t,
        )
        assert not res.is_leap_detected
        assert res.state == KillerKinematicState.GROUNDED
        assert abs(res.vertical_velocity_px_s) < 5.0


def test_parabolic_leap_detected():
    """Menguji lompatan parabolik dengan lonjakan vertikal tajam berhasil terdeteksi sebagai Leap."""
    detector = TrajectoryActionDetector(velocity_threshold_px_s=-180.0, elevation_threshold_px=35.0)
    t = 1000.0

    # 1. Posisi awal di tanah (Y=400, centroid_y = 460)
    for _ in range(5):
        t += 0.04
        detector.update(bbox=(250, 400, 60, 120), confidence=0.88, timestamp=t)

    assert detector.ground_y is not None

    # 2. Frame take-off / lonjakan cepat ke atas: Y melesat dari 400 ke 320 dalam 0.04s (-2000 px/s, elevasi 80 px)
    t += 0.04
    res = detector.update(bbox=(250, 320, 60, 120), confidence=0.90, timestamp=t)

    assert res.is_leap_detected
    assert res.state == KillerKinematicState.AIRBORNE
    assert res.vertical_velocity_px_s <= -180.0
    assert res.elevation_px >= 35.0


def test_debounce_lockout():
    """Menguji perlindungan debounce 15 detik mencegah multi-trigger saat killer sedang melompat berulang."""
    detector = TrajectoryActionDetector(debounce_seconds=15.0)
    t = 1000.0

    # Grounding
    for _ in range(3):
        t += 0.04
        detector.update(bbox=(250, 400, 60, 120), confidence=0.88, timestamp=t)

    # First leap trigger
    t += 0.04
    res1 = detector.update(bbox=(250, 310, 60, 120), confidence=0.92, timestamp=t)
    assert res1.is_leap_detected

    # Lompatan kedua 2 detik kemudian (masih dalam jendela debounce 15s)
    t += 2.0
    res2 = detector.update(bbox=(250, 300, 60, 120), confidence=0.92, timestamp=t)
    assert not res2.is_leap_detected
    assert "Debounce active" in res2.explanation

    # Setelah 16 detik (lewat batas debounce), lompatan baru diizinkan
    t += 16.0
    # Reset grounding
    detector.update(bbox=(250, 400, 60, 120), confidence=0.85, timestamp=t)
    t += 0.04
    res3 = detector.update(bbox=(250, 310, 60, 120), confidence=0.90, timestamp=t)
    assert res3.is_leap_detected


def test_target_loss_handling():
    """Menguji penanganan ketika target visual killer menghilang dari layar."""
    detector = TrajectoryActionDetector()
    t = 1000.0

    # Grounded target
    detector.update(bbox=(250, 400, 60, 120), confidence=0.85, timestamp=t)

    # Target hilang sejenak
    t += 0.04
    res = detector.update(bbox=None, confidence=0.0, timestamp=t)
    assert not res.is_leap_detected
    assert "not visible" in res.explanation

    # Target hilang lebih dari 1.0 detik -> reset
    t += 1.5
    detector.update(bbox=None, confidence=0.0, timestamp=t)
    assert detector.state == KillerKinematicState.UNKNOWN


def test_airborne_state_detected_at_apex():
    """Menguji killer yang melayang di udara (misal di puncak lonjakan) tetap memicu Leap meski lonjakan awal terlewat."""
    detector = TrajectoryActionDetector(velocity_threshold_px_s=-180.0, elevation_threshold_px=30.0)
    t = 1000.0

    # 1. Baseline tanah
    for _ in range(5):
        t += 0.04
        detector.update(bbox=(300, 500, 60, 120), confidence=0.85, timestamp=t)

    # 2. Killer melayang tinggi di udara (Y=380, elevasi 120 px) dengan kecepatan lambat di puncak (apex Vy ~ 0)
    # Frame 1 melayang
    t += 0.04
    res1 = detector.update(bbox=(300, 380, 60, 100), confidence=0.88, timestamp=t)
    # Boleh langsung terpicu karena HighAirborne (elevation >= 40 px)
    assert res1.is_leap_detected
    assert res1.state == KillerKinematicState.AIRBORNE
