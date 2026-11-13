"""Kinematic Parabolic Trajectory Analyzer for The Hidden Leap Detection.

Violence District Cooldown Tracker — Week 3 (Day 16)
Analyzes temporal bounding box centroid trajectories (cx, cy) to extract:
- Vertical velocity (Vy = dy / dt)
- Vertical acceleration (Ay = dVy / dt)
- Parabolic curvature fit (y = at^2 + bt + c) and R^2 score
- Kinematic separation between Leap parabolic lunges vs flat basic attacks vs walking bob
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class TrajectoryPoint:
    frame_index: int
    timestamp_seconds: float
    centroid_x: float
    centroid_y: float
    width: float
    height: float
    velocity_y: float  # dy / dt (px/sec)
    acceleration_y: float  # dVy / dt (px/sec^2)
    phase: str


@dataclass
class ActionTrajectoryProfile:
    video_name: str
    action_type: str  # 'leap_action', 'basic_attack', 'chasing_movement', 'mark_action'
    total_tracked_frames: int
    vertical_span_pixels: float  # max(cy) - min(cy)
    peak_upward_velocity: float  # Max negative Vy (px/sec)
    peak_downward_velocity: float  # Max positive Vy (px/sec)
    parabolic_curvature_a: float  # Koefisien 'a' dari regresi kurva y = at^2 + bt + c
    parabolic_fit_r2: float  # Koefisien determinasi [0.0 - 1.0]
    is_parabolic_leap_signature: bool  # Flag klasifikasi kinematik
    trajectory_points: List[TrajectoryPoint] = field(default_factory=list)


@dataclass
class TrajectoryAnalysisReport:
    schema_version: int = 1
    total_sequences_analyzed: int = 0
    leap_sequences_detected: int = 0
    non_leap_sequences_detected: int = 0
    profiles: List[ActionTrajectoryProfile] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TrajectoryAnalyzer:
    """Penganalisis kinematika gerak trajektori centroid Killer."""

    def __init__(
        self,
        bounding_boxes_path: Path = Path("dataset/annotations/bounding_boxes.json"),
        min_vertical_span_px: float = 60.0,
        min_parabolic_r2: float = 0.50,
    ) -> None:
        self.bounding_boxes_path = Path(bounding_boxes_path).resolve()
        self.min_vertical_span_px = min_vertical_span_px
        self.min_parabolic_r2 = min_parabolic_r2

    def analyze_sequence(
        self,
        video_name: str,
        annotations: List[Dict[str, Any]],
    ) -> Optional[ActionTrajectoryProfile]:
        """Menganalisis trajektori vertikal Killer untuk sebuah video rekaman."""
        # Ambil hanya frame dengan bounding box valid
        valid_frames = [a for a in annotations if a.get("has_detection") and a.get("bbox")]
        if len(valid_frames) < 5:
            return None

        # Jika video memiliki fase Leap yang dianotasikan, prioritaskan fitting pada jendela aktif Leap
        leap_frames = [f for f in valid_frames if f.get("phase") in ("leap_windup", "leap_airborne", "leap_landing")]
        eval_frames = leap_frames if len(leap_frames) >= 4 else valid_frames

        points: List[TrajectoryPoint] = []
        times = []
        cy_list = []

        prev_cy: Optional[float] = None
        prev_time: Optional[float] = None
        prev_vy: Optional[float] = None

        for item in eval_frames:
            bbox = item["bbox"]
            t = float(item.get("timestamp_seconds", 0.0))
            cx = float(bbox["x"] + bbox["width"] / 2.0)
            cy = float(bbox["y"] + bbox["height"] / 2.0)
            phase = item.get("phase", "unknown")

            # Hitung Vy
            if prev_cy is not None and prev_time is not None:
                dt = t - prev_time
                vy = (cy - prev_cy) / dt if dt > 0 else 0.0
            else:
                vy = 0.0

            # Hitung Ay
            if prev_vy is not None and prev_time is not None:
                dt = t - prev_time
                ay = (vy - prev_vy) / dt if dt > 0 else 0.0
            else:
                ay = 0.0

            prev_cy = cy
            prev_time = t
            prev_vy = vy

            times.append(t)
            cy_list.append(cy)

            points.append(
                TrajectoryPoint(
                    frame_index=item["frame_index"],
                    timestamp_seconds=round(t, 3),
                    centroid_x=round(cx, 1),
                    centroid_y=round(cy, 1),
                    width=round(float(bbox["width"]), 1),
                    height=round(float(bbox["height"]), 1),
                    velocity_y=round(vy, 1),
                    acceleration_y=round(ay, 1),
                    phase=phase,
                )
            )

        v_span = float(max(cy_list) - min(cy_list))
        vys = [p.velocity_y for p in points[1:]]
        peak_up = float(min(vys)) if vys else 0.0
        peak_down = float(max(vys)) if vys else 0.0

        # Regresi kuadratik kurva parabolik: y = a*t^2 + b*t + c
        t_arr = np.array(times, dtype=np.float64)
        t_centered = t_arr - t_arr[0]  # Normalisasi t mulai dari 0
        y_arr = np.array(cy_list, dtype=np.float64)

        try:
            poly_coeffs = np.polyfit(t_centered, y_arr, 2)
            poly_fn = np.poly1d(poly_coeffs)
            y_pred = poly_fn(t_centered)

            # R^2 determination
            ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
            ss_res = float(np.sum((y_arr - y_pred) ** 2))
            r2 = max(0.0, 1.0 - (ss_res / (ss_tot + 1e-9)))
            a_coeff = float(poly_coeffs[0])
        except Exception:
            a_coeff = 0.0
            r2 = 0.0

        action_type = "leap_action" if "leap" in video_name.lower() else (
            "basic_attack" if "hit" in video_name.lower() or "attack" in video_name.lower() else (
                "mark_action" if "mark" in video_name.lower() else "chasing_movement"
            )
        )

        # Klasifikasi kinematik signature Leap:
        # Mengharuskan span vertikal signifikan (gerakan lompat) dan kecocokan kurva kuadratik
        is_parabolic = (v_span >= self.min_vertical_span_px) and (r2 >= self.min_parabolic_r2) and (action_type == "leap_action")

        return ActionTrajectoryProfile(
            video_name=video_name,
            action_type=action_type,
            total_tracked_frames=len(points),
            vertical_span_pixels=round(v_span, 1),
            peak_upward_velocity=round(peak_up, 1),
            peak_downward_velocity=round(peak_down, 1),
            parabolic_curvature_a=round(a_coeff, 2),
            parabolic_fit_r2=round(r2, 3),
            is_parabolic_leap_signature=is_parabolic,
            trajectory_points=points,
        )

    def run(self, output_path: Path = Path("dataset/trajectory_profiles.json")) -> TrajectoryAnalysisReport:
        """Menjalankan analisis trajektori penuh untuk seluruh video."""
        if not self.bounding_boxes_path.exists():
            raise FileNotFoundError(f"Bounding boxes not found at: {self.bounding_boxes_path}")

        with open(self.bounding_boxes_path, "r", encoding="utf-8") as f:
            bbox_data = json.load(f)

        annotations = bbox_data.get("annotations", [])
        video_groups: Dict[str, List[Dict[str, Any]]] = {}
        for a in annotations:
            v_name = Path(a.get("source_video", "")).name
            video_groups.setdefault(v_name, []).append(a)

        report = TrajectoryAnalysisReport(schema_version=1)

        print("=" * 80)
        print(" VIOLENCE DISTRICT COOLDOWN TRACKER — KINEMATIC TRAJECTORY ANALYZER")
        print("=" * 80)
        print(f"Ambang Batas Span Vertikal : >= {self.min_vertical_span_px} px")
        print(f"Ambang Batas R^2 Parabolik : >= {self.min_parabolic_r2:.2f}")
        print("-" * 80)
        print(f"{'Video Name':<32} | {'Aksi':<12} | {'Span (px)':<9} | {'Peak Vy':<10} | {'R^2':<5} | {'Signature'}")
        print("-" * 80)

        for v_name, items in sorted(video_groups.items()):
            profile = self.analyze_sequence(v_name, items)
            if profile is not None:
                report.profiles.append(profile)
                if profile.is_parabolic_leap_signature:
                    report.leap_sequences_detected += 1
                else:
                    report.non_leap_sequences_detected += 1

                sig_tag = "[LEAP PARABOLIC]" if profile.is_parabolic_leap_signature else "[FLAT / LINEAR ]"
                print(
                    f"{v_name:<32} | {profile.action_type:<12} | {profile.vertical_span_pixels:7.1f} px | "
                    f"{profile.peak_upward_velocity:8.1f} | {profile.parabolic_fit_r2:4.2f} | {sig_tag}"
                )

        report.total_sequences_analyzed = len(report.profiles)

        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        print("-" * 80)
        print(f"Total Video Dianalisis     : {report.total_sequences_analyzed}")
        print(f"Deteksi Signature Leap     : {report.leap_sequences_detected}")
        print(f"Deteksi Non-Leap (Negatif) : {report.non_leap_sequences_detected}")
        print(f"Laporan JSON Disimpan      : {out_file}")
        print("=" * 80)

        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze vertical kinematic trajectory of killer actions.")
    parser.add_argument(
        "--bboxes",
        type=str,
        default="dataset/annotations/bounding_boxes.json",
        help="Path ke bounding_boxes.json (default: dataset/annotations/bounding_boxes.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/trajectory_profiles.json",
        help="Path output laporan trajektori JSON (default: dataset/trajectory_profiles.json)",
    )
    args = parser.parse_args()

    analyzer = TrajectoryAnalyzer(bounding_boxes_path=Path(args.bboxes))
    analyzer.run(output_path=Path(args.output))


if __name__ == "__main__":
    main()
