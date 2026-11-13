"""In-game Golden Keyframe Profiler & Feature Similarity Evaluator.

Violence District Cooldown Tracker — Week 3 (Day 15 Langkah 3)
Compares manual in-game golden keyframes (PNG) with extracted video action frames
to evaluate structural similarity, color histogram correlation, and ORB feature consistency.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class KeyframeMatchResult:
    golden_keyframe: str
    target_frame_id: str
    target_phase: str
    target_label: str
    histogram_correlation: float  # [0.0 - 1.0], metode cv2.HISTCMP_CORREL
    edge_gradient_similarity: float  # [0.0 - 1.0], kemiripan magnitude gradien Sobel


@dataclass
class GoldenKeyframeSummary:
    golden_keyframe: str
    width: int
    height: int
    category: str
    best_matching_frame: str
    best_matching_phase: str
    highest_correlation: float
    mean_leap_correlation: float
    mean_negative_correlation: float
    separation_margin: float


@dataclass
class KeyframeValidationReport:
    schema_version: int = 1
    total_golden_keyframes: int = 0
    golden_summaries: List[GoldenKeyframeSummary] = field(default_factory=list)
    detailed_matches: List[KeyframeMatchResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KeyframeProfiler:
    """Evaluator kemiripan fitur visual antara citra golden in-game dan frame video."""

    def __init__(
        self,
        golden_dir: Path = Path("database/dataset/HIDDEN/PNG/INGAME"),
        manifest_path: Path = Path("dataset/extracted/manifest.json"),
    ) -> None:
        self.golden_dir = Path(golden_dir).resolve()
        self.manifest_path = Path(manifest_path).resolve()

    def compute_color_hist(self, img: np.ndarray) -> np.ndarray:
        """Menghitung histogram HSV ternormalisasi 2D (H-S)."""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist

    def compute_edge_gradient_similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Menghitung kemiripan rata-rata magnitudo gradien Sobel (kontur tubuh)."""
        g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        g2_res = cv2.resize(g2, (g1.shape[1], g1.shape[0]))

        sobel1 = cv2.Sobel(g1, cv2.CV_32F, 1, 1, ksize=3)
        sobel2 = cv2.Sobel(g2_res, cv2.CV_32F, 1, 1, ksize=3)

        norm1 = np.linalg.norm(sobel1)
        norm2 = np.linalg.norm(sobel2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        dot = np.sum(sobel1 * sobel2)
        return float(np.clip(dot / (norm1 * norm2), 0.0, 1.0))

    def evaluate(self, sample_limit_per_phase: int = 10) -> KeyframeValidationReport:
        """Menjalankan evaluasi kemiripan lintas golden keyframes dan frame terekstrak."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        dataset_root = self.manifest_path.parent.parent
        extracted_frames = manifest_data.get("frames", [])

        # Ambil sampel representatif per fase untuk efisiensi
        sampled_frames: List[Dict[str, Any]] = []
        phase_groups: Dict[str, List[Dict[str, Any]]] = {}
        for f in extracted_frames:
            phase_groups.setdefault(f.get("phase", "unknown"), []).append(f)

        for phase, items in phase_groups.items():
            step = max(1, len(items) // sample_limit_per_phase)
            sampled_frames.extend(items[::step][:sample_limit_per_phase])

        report = KeyframeValidationReport(total_golden_keyframes=0)
        golden_files = sorted(self.golden_dir.glob("*.png"))
        report.total_golden_keyframes = len(golden_files)

        for g_file in golden_files:
            g_img = cv2.imread(str(g_file))
            if g_img is None:
                continue

            gh, gw = g_img.shape[:2]
            g_hist = self.compute_color_hist(g_img)
            cat = "leap" if "leap" in g_file.name.lower() else ("mark" if "mark" in g_file.name.lower() else "stay")

            best_match_id = ""
            best_phase = ""
            best_corr = -1.0
            leap_corrs = []
            neg_corrs = []

            for frame_info in sampled_frames:
                frame_rel = frame_info.get("relative_path", "")
                f_path = (dataset_root / frame_rel).resolve()
                if not f_path.exists():
                    continue

                f_img = cv2.imread(str(f_path))
                if f_img is None:
                    continue

                f_hist = self.compute_color_hist(f_img)
                corr = float(cv2.compareHist(g_hist, f_hist, cv2.HISTCMP_CORREL))
                edge_sim = self.compute_edge_gradient_similarity(g_img, f_img)

                phase = frame_info.get("phase", "unknown")
                label = frame_info.get("label", "unknown")

                if "leap" in phase:
                    leap_corrs.append(corr)
                else:
                    neg_corrs.append(corr)

                if corr > best_corr:
                    best_corr = corr
                    best_match_id = frame_info.get("frame_id", "")
                    best_phase = phase

                report.detailed_matches.append(
                    KeyframeMatchResult(
                        golden_keyframe=g_file.name,
                        target_frame_id=frame_info.get("frame_id", ""),
                        target_phase=phase,
                        target_label=label,
                        histogram_correlation=round(corr, 3),
                        edge_gradient_similarity=round(edge_sim, 3),
                    )
                )

            mean_leap = round(sum(leap_corrs) / len(leap_corrs), 3) if leap_corrs else 0.0
            mean_neg = round(sum(neg_corrs) / len(neg_corrs), 3) if neg_corrs else 0.0
            margin = round(mean_leap - mean_neg, 3)

            report.golden_summaries.append(
                GoldenKeyframeSummary(
                    golden_keyframe=g_file.name,
                    width=gw,
                    height=gh,
                    category=cat,
                    best_matching_frame=best_match_id,
                    best_matching_phase=best_phase,
                    highest_correlation=round(best_corr, 3),
                    mean_leap_correlation=mean_leap,
                    mean_negative_correlation=mean_neg,
                    separation_margin=margin,
                )
            )

        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate visual similarity between golden PNG keyframes and video frames.")
    parser.add_argument(
        "--golden-dir",
        type=str,
        default="database/dataset/HIDDEN/PNG/INGAME",
        help="Direktori citra in-game golden (default: database/dataset/HIDDEN/PNG/INGAME)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="dataset/extracted/manifest.json",
        help="Path ke berkas extracted manifest.json (default: dataset/extracted/manifest.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/keyframe_validation.json",
        help="Path output laporan validasi (default: dataset/keyframe_validation.json)",
    )
    args = parser.parse_args()

    profiler = KeyframeProfiler(golden_dir=Path(args.golden_dir), manifest_path=Path(args.manifest))
    report = profiler.evaluate()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print(" VIOLENCE DISTRICT COOLDOWN TRACKER — GOLDEN KEYFRAME VALIDATION REPORT")
    print("=" * 80)
    print(f"Total Golden Keyframes Dievaluasi : {report.total_golden_keyframes}")
    print("-" * 80)
    print(f"{'Golden Keyframe':<22} | {'Kategori':<6} | {'Best Match Frame':<30} | {'Fase':<14} | {'Korelasi'}")
    print("-" * 80)

    for s in report.golden_summaries:
        print(f"{s.golden_keyframe:<22} | {s.category:<6} | {s.best_matching_frame:<30} | {s.best_matching_phase:<14} | {s.highest_correlation:5.3f}")

    print("=" * 80)
    print(f"Laporan JSON disimpan ke: {out_path.resolve()}")


if __name__ == "__main__":
    main()
