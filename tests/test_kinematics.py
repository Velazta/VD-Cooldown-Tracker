"""Unit tests for Kinematics Trajectory Fitting (detection/kinematics.py)."""

import numpy as np
import pytest
from detection.kinematics import fit_parabola, compensate_camera_motion


def test_fit_parabola_ideal_trajectory():
    # Synthetic physical leap: t in [0.0, 1.0]s, apex at t=0.5s
    # In screen coordinates: y(t) = 4.0 * (t - 0.5)^2 + 0.2 = 4.0*t^2 - 4.0*t + 1.2
    times = np.linspace(0.0, 1.0, 30)
    y_values = 4.0 * (times - 0.5) ** 2 + 0.2

    res = fit_parabola(times, y_values)
    assert res is not None
    assert pytest.approx(res.r2, 0.01) == 1.0
    assert pytest.approx(res.apex_time, 0.02) == 0.5
    assert res.is_valid_parabola is True
    assert res.a > 0.0
    assert res.vertical_span > 0.5


def test_fit_parabola_rejects_flat_or_linear_motion():
    # Linear walking or horizontal motion
    times = np.linspace(0.0, 1.0, 30)
    y_values = 0.5 + 0.01 * times  # flat line with tiny slope

    res = fit_parabola(times, y_values)
    assert res is not None
    # Extremely small vertical span or linear -> not a valid jump parabola
    assert res.vertical_span < 0.02


def test_compensate_camera_motion():
    # Camera bobs up and down by +0.05
    survivor_ys = [0.50, 0.52, 0.55, 0.52, 0.50]
    # Stationary Killer appears to move because camera moves
    hidden_ys = [0.30, 0.32, 0.35, 0.32, 0.30]

    compensated = compensate_camera_motion(hidden_ys, survivor_ys)
    # Relative Y is completely flat at -0.20!
    for val in compensated:
        assert pytest.approx(val, 0.001) == -0.20
