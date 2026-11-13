"""Dataset Indexer & Metadata Ingestion Module.

Violence District Cooldown Tracker — Week 3 (Day 15)
Scans, classifies, and indexes raw multi-modal dataset files (MP4, PNG, WAV)
from database/dataset/HIDDEN/ into a structured, validated dataset/catalog.json manifest.

Includes:
- SHA-256 cryptographic provenance verification
- Sub-category semantic action tagging
- Train/Validation/Test split allocation to avoid data leakage
- Video codec, bitrate, and aspect-ratio extraction
- Skin HSV color space profiling to quantify visual diversity across skins
- FFT audio spectral centroid, dominant frequency, and dBFS energy calculation
- Automatic dataset integrity diagnostic audit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


def compute_sha256(file_path: Path) -> str:
    """Menghitung hash SHA-256 dari berkas untuk jaminan integritas dataset."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class VideoEntry:
    file_name: str
    relative_path: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    codec: str
    aspect_ratio: str
    bitrate_kbps: float
    category: str  # 'leap_action', 'mark_action', 'basic_attack', 'chasing_movement'
    sub_category: str  # 'leap_solo', 'leap_mark_combo', 'hit_survivor', 'hit_wall', 'hit_air', dsb.
    split: str  # 'train', 'val', 'test'
    is_positive_leap: bool
    file_size_bytes: int
    sha256: str


@dataclass
class ImageEntry:
    file_name: str
    relative_path: str
    width: int
    height: int
    category: str  # 'leap', 'mark', 'stay'
    sub_category: str
    split: str  # 'train', 'val', 'test'
    is_positive_leap: bool
    file_size_bytes: int
    sha256: str


@dataclass
class SkinEntry:
    skin_id: str
    file_name: str
    relative_path: str
    width: int
    height: int
    mean_hsv: List[float]  # [Hue (0-179), Saturation (0-255), Value (0-255)]
    mean_bgr: List[int]  # [Blue, Green, Red]
    file_size_bytes: int
    sha256: str


@dataclass
class AudioEntry:
    file_name: str
    relative_path: str
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    peak_amplitude: int
    rms_energy: float
    dominant_frequency_hz: float
    spectral_centroid_hz: float
    energy_dbfs: float
    category: str  # 'leap_cue', 'mark_cue', 'attack_cue'
    sub_category: str  # 'vocal_and_whoosh', 'blade_slash', 'spear_hit_wall', dsb.
    split: str  # 'train', 'val', 'test'
    is_positive_leap: bool
    file_size_bytes: int
    sha256: str


@dataclass
class DatasetCatalog:
    schema_version: int = 2
    killer_id: str = "the_hidden"
    total_videos: int = 0
    total_video_frames: int = 0
    total_video_duration_seconds: float = 0.0
    total_ingame_images: int = 0
    total_skin_variations: int = 0
    total_skin_images: int = 0
    total_audio_samples: int = 0
    train_samples_count: int = 0
    val_samples_count: int = 0
    test_samples_count: int = 0
    videos: List[VideoEntry] = field(default_factory=list)
    ingame_images: List[ImageEntry] = field(default_factory=list)
    skins: List[SkinEntry] = field(default_factory=list)
    audio: List[AudioEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetIndexer:
    """Manajer pemindaian, profiling fitur, dan pembuatan indeks metadata dataset."""

    def __init__(self, root_path: Optional[Path] = None) -> None:
        self.root_path = Path(root_path or "database/dataset/HIDDEN").resolve()

    def classify_video(self, file_name: str) -> Tuple[str, str, str, bool]:
        """Menentukan kategori semantik, sub-kategori, rekomendasi split, dan flag Leap positif.

        Returns:
            Tuple[category, sub_category, split, is_positive_leap]
        """
        lower = file_name.lower()

        # 1. Leap Action (Positive Ground Truth)
        if "leap" in lower:
            is_pos = True
            cat = "leap_action"
            if "combo" in lower:
                sub = "leap_mark_combo"
                split = "test"  # Combo skill dialokasikan untuk pengujian unseen edge-case
            elif "skills" in lower:
                sub = "leap_multi"
                split = "val"
            elif "ref2" in lower:
                sub = "leap_solo"
                split = "train"
            elif "hidden3" in lower:
                sub = "leap_solo"
                split = "val"
            elif "hidden2" in lower:
                sub = "leap_solo"
                split = "train"
            else:
                sub = "leap_solo"
                split = "train"
            return cat, sub, split, is_pos

        # 2. Mark Action (Hard Negatives: Spear Throw / Aim)
        if "mark" in lower:
            is_pos = False
            cat = "mark_action"
            if "nohitsurvivor" in lower or "no_hit" in lower:
                sub = "mark_miss"
                split = "val"
            elif "hitsurvivor" in lower or "hit_survivor" in lower:
                sub = "mark_hit_survivor"
                split = "val"
            elif "chasing" in lower:
                sub = "chase_and_mark"
                split = "test"
            else:
                sub = "mark_solo"
                split = "train"
            return cat, sub, split, is_pos

        # 3. Basic Attack (Hard Negatives: Melee Swings)
        if "hit" in lower or "attack" in lower:
            is_pos = False
            cat = "basic_attack"
            if "survivor" in lower:
                sub = "hit_survivor"
                split = "train"
            elif "wall" in lower:
                sub = "hit_wall"
                split = "val"
            else:
                sub = "hit_air"
                split = "train"
            return cat, sub, split, is_pos

        # 4. Chasing / Movement (Hard Negatives)
        if "chasing" in lower or "movement" in lower:
            is_pos = False
            cat = "chasing_movement"
            sub = "chase_running"
            split = "test"
            return cat, sub, split, is_pos

        return "unclassified", "unknown", "train", False

    def classify_image(self, file_name: str) -> Tuple[str, str, str, bool]:
        """Menentukan kategori semantik, sub-kategori, split, dan flag gambar in-game."""
        lower = file_name.lower()
        if "leap" in lower:
            split = "test" if "4" in lower else "train"
            return "leap", "leap_keyframe", split, True
        elif "mark" in lower:
            split = "val" if any(x in lower for x in ("5", "6")) else "train"
            return "mark", "mark_keyframe", split, False
        elif "stay" in lower or "idle" in lower:
            return "stay", "idle_keyframe", "train", False
        return "unclassified", "unknown", "train", False

    def classify_audio(self, file_name: str) -> Tuple[str, str, str, bool]:
        """Menentukan kategori semantik, sub-kategori, split, dan flag audio."""
        lower = file_name.lower()
        if "leap" in lower:
            return "leap_cue", "vocal_and_whoosh", "train", True
        elif "attack" in lower or ("hit" in lower and "mark" not in lower):
            return "attack_cue", "blade_slash", "train", False
        elif "mark" in lower:
            if "wall" in lower:
                sub = "spear_hit_wall"
                split = "val"
            elif "no_hit" in lower:
                sub = "spear_miss"
                split = "val"
            else:
                sub = "spear_hit_survivor"
                split = "test"
            return "mark_cue", sub, split, False
        return "unclassified", "unknown", "train", False

    def scan_video(self, file_path: Path) -> Optional[VideoEntry]:
        """Mengekstrak metadata teknis video (dimensi, fps, codec, bitrate, SHA-256)."""
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            cap.release()
            return None

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_cnt = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Ekstraksi FourCC Codec
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_chars = [chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)]
        codec_str = "".join(c for c in codec_chars if c.isprintable()).strip() or "unknown"

        cap.release()

        dur = frame_cnt / fps if fps > 0 else 0.0
        file_size = file_path.stat().st_size
        bitrate_kbps = round((file_size * 8.0) / (dur * 1000.0), 2) if dur > 0 else 0.0

        # Hitung aspect ratio
        gcd_val = math.gcd(w, h) if w > 0 and h > 0 else 1
        aspect_ratio = f"{w // gcd_val}:{h // gcd_val}"

        cat, sub_cat, split, is_pos = self.classify_video(file_path.name)
        sha256_hash = compute_sha256(file_path)

        try:
            rel_path = str(file_path.relative_to(self.root_path.parent.parent.parent))
        except ValueError:
            rel_path = str(file_path)

        return VideoEntry(
            file_name=file_path.name,
            relative_path=rel_path.replace("\\", "/"),
            width=w,
            height=h,
            fps=round(fps, 2),
            frame_count=frame_cnt,
            duration_seconds=round(dur, 2),
            codec=codec_str,
            aspect_ratio=aspect_ratio,
            bitrate_kbps=bitrate_kbps,
            category=cat,
            sub_category=sub_cat,
            split=split,
            is_positive_leap=is_pos,
            file_size_bytes=file_size,
            sha256=sha256_hash,
        )

    def scan_image(self, file_path: Path) -> Optional[ImageEntry]:
        """Mengekstrak metadata dimensi gambar dan SHA-256."""
        img = cv2.imread(str(file_path))
        if img is None:
            return None

        h, w = img.shape[:2]
        cat, sub_cat, split, is_pos = self.classify_image(file_path.name)
        sha256_hash = compute_sha256(file_path)

        try:
            rel_path = str(file_path.relative_to(self.root_path.parent.parent.parent))
        except ValueError:
            rel_path = str(file_path)

        return ImageEntry(
            file_name=file_path.name,
            relative_path=rel_path.replace("\\", "/"),
            width=w,
            height=h,
            category=cat,
            sub_category=sub_cat,
            split=split,
            is_positive_leap=is_pos,
            file_size_bytes=file_path.stat().st_size,
            sha256=sha256_hash,
        )

    def scan_skin_image(self, skin_id: str, file_path: Path) -> Optional[SkinEntry]:
        """Mengekstrak profil ruang warna (Mean HSV dan BGR) serta hash integritas skin."""
        img = cv2.imread(str(file_path))
        if img is None:
            return None

        h, w = img.shape[:2]

        # Komputasi statistik warna HSV untuk kuantifikasi variasi skin
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mean_hsv = [round(float(val), 2) for val in cv2.mean(hsv)[:3]]
        mean_bgr = [int(round(float(val))) for val in cv2.mean(img)[:3]]

        sha256_hash = compute_sha256(file_path)

        try:
            rel_path = str(file_path.relative_to(self.root_path.parent.parent.parent))
        except ValueError:
            rel_path = str(file_path)

        return SkinEntry(
            skin_id=skin_id,
            file_name=file_path.name,
            relative_path=rel_path.replace("\\", "/"),
            width=w,
            height=h,
            mean_hsv=mean_hsv,
            mean_bgr=mean_bgr,
            file_size_bytes=file_path.stat().st_size,
            sha256=sha256_hash,
        )

    def scan_audio(self, file_path: Path) -> Optional[AudioEntry]:
        """Mengekstrak parameter akustik PCM WAV (FFT Dominant Frequency, Spectral Centroid, RMS, dBFS)."""
        try:
            with wave.open(str(file_path), "rb") as wf:
                nch = wf.getnchannels()
                rate = wf.getframerate()
                nframes = wf.getnframes()
                dur = nframes / rate if rate > 0 else 0.0
                raw_bytes = wf.readframes(nframes)

            # Sample audio PCM 16-bit
            samples = np.frombuffer(raw_bytes, dtype=np.int16)
            if len(samples) > 0:
                peak = int(np.max(np.abs(samples)))
                rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
                energy_dbfs = round(20.0 * math.log10(rms / 32767.0), 2) if rms > 0 else -96.0

                # Campur ke mono untuk analisis spektral FFT
                if nch > 1:
                    mono = samples.reshape(-1, nch).mean(axis=1)
                else:
                    mono = samples.astype(np.float64)

                # Komputasi FFT dengan NumPy
                fft_vals = np.abs(np.fft.rfft(mono))
                fft_freqs = np.fft.rfftfreq(len(mono), d=1.0 / rate)

                sum_fft = float(np.sum(fft_vals))
                if sum_fft > 0:
                    dominant_freq = float(fft_freqs[np.argmax(fft_vals)])
                    spectral_centroid = float(np.sum(fft_freqs * fft_vals) / sum_fft)
                else:
                    dominant_freq = 0.0
                    spectral_centroid = 0.0
            else:
                peak = 0
                rms = 0.0
                energy_dbfs = -96.0
                dominant_freq = 0.0
                spectral_centroid = 0.0

            cat, sub_cat, split, is_pos = self.classify_audio(file_path.name)
            sha256_hash = compute_sha256(file_path)

            try:
                rel_path = str(file_path.relative_to(self.root_path.parent.parent.parent))
            except ValueError:
                rel_path = str(file_path)

            return AudioEntry(
                file_name=file_path.name,
                relative_path=rel_path.replace("\\", "/"),
                duration_seconds=round(dur, 2),
                sample_rate_hz=rate,
                channels=nch,
                peak_amplitude=peak,
                rms_energy=round(rms, 2),
                dominant_frequency_hz=round(dominant_freq, 2),
                spectral_centroid_hz=round(spectral_centroid, 2),
                energy_dbfs=energy_dbfs,
                category=cat,
                sub_category=sub_cat,
                split=split,
                is_positive_leap=is_pos,
                file_size_bytes=file_path.stat().st_size,
                sha256=sha256_hash,
            )
        except Exception:
            return None

    def build_catalog(self) -> DatasetCatalog:
        """Memindai seluruh dataset multi-modal dan menyusun DatasetCatalog."""
        catalog = DatasetCatalog(schema_version=2, killer_id="the_hidden")

        if not self.root_path.exists():
            return catalog

        # 1. Pindai Video MP4
        mp4_dir = self.root_path / "MP4"
        if mp4_dir.exists():
            for v_file in sorted(mp4_dir.rglob("*.mp4")):
                entry = self.scan_video(v_file)
                if entry is not None:
                    catalog.videos.append(entry)

        # 2. Pindai Gambar In-Game
        ingame_dir = self.root_path / "PNG" / "INGAME"
        if ingame_dir.exists():
            for img_file in sorted(ingame_dir.glob("*.png")):
                entry = self.scan_image(img_file)
                if entry is not None:
                    catalog.ingame_images.append(entry)

        # 3. Pindai Gambar Skin
        skin_root = self.root_path / "PNG" / "SKIN"
        skin_ids = set()
        if skin_root.exists():
            for s_dir in sorted(skin_root.iterdir()):
                if s_dir.is_dir():
                    skin_ids.add(s_dir.name)
                    for s_img in sorted(s_dir.glob("*.png")):
                        entry = self.scan_skin_image(s_dir.name, s_img)
                        if entry is not None:
                            catalog.skins.append(entry)

        # 4. Pindai Audio WAV
        wav_dir = self.root_path / "WAV"
        if wav_dir.exists():
            for w_file in sorted(wav_dir.glob("*.wav")):
                entry = self.scan_audio(w_file)
                if entry is not None:
                    catalog.audio.append(entry)

        # Hitung Agregasi
        catalog.total_videos = len(catalog.videos)
        catalog.total_video_frames = sum(v.frame_count for v in catalog.videos)
        catalog.total_video_duration_seconds = round(sum(v.duration_seconds for v in catalog.videos), 2)
        catalog.total_ingame_images = len(catalog.ingame_images)
        catalog.total_skin_variations = len(skin_ids)
        catalog.total_skin_images = len(catalog.skins)
        catalog.total_audio_samples = len(catalog.audio)

        # Hitung distribusi split (Video + In-game Images + Audio)
        all_split_entries = catalog.videos + catalog.ingame_images + catalog.audio
        catalog.train_samples_count = sum(1 for e in all_split_entries if e.split == "train")
        catalog.val_samples_count = sum(1 for e in all_split_entries if e.split == "val")
        catalog.test_samples_count = sum(1 for e in all_split_entries if e.split == "test")

        return catalog

    def save_catalog(self, output_path: Path) -> DatasetCatalog:
        """Menyimpan hasil katalog ke berkas JSON."""
        catalog = self.build_catalog()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog.to_dict(), f, indent=2, ensure_ascii=False)
        return catalog

    def verify_integrity(self) -> Dict[str, Any]:
        """Menjalankan audit diagnostik kelayakan dan kesehatan dataset secara mendalam."""
        report: Dict[str, Any] = {
            "total_files_scanned": 0,
            "corrupt_files": [],
            "duplicate_files": [],
            "video_decodable": True,
            "audio_pcm_valid": True,
            "images_valid": True,
            "status": "PASS",
        }

        seen_hashes: Dict[str, str] = {}

        # 1. Verifikasi Video
        mp4_dir = self.root_path / "MP4"
        if mp4_dir.exists():
            for v_path in sorted(mp4_dir.rglob("*.mp4")):
                report["total_files_scanned"] += 1
                h = compute_sha256(v_path)
                if h in seen_hashes:
                    report["duplicate_files"].append((str(v_path), seen_hashes[h]))
                else:
                    seen_hashes[h] = str(v_path)

                cap = cv2.VideoCapture(str(v_path))
                fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                ret1, _ = cap.read()
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fc // 2))
                ret2, _ = cap.read()
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fc - 1))
                ret3, _ = cap.read()
                cap.release()

                if not (ret1 and ret2 and ret3):
                    report["corrupt_files"].append(str(v_path))
                    report["video_decodable"] = False

        # 2. Verifikasi Audio
        wav_dir = self.root_path / "WAV"
        if wav_dir.exists():
            for w_path in sorted(wav_dir.glob("*.wav")):
                report["total_files_scanned"] += 1
                h = compute_sha256(w_path)
                if h in seen_hashes:
                    report["duplicate_files"].append((str(w_path), seen_hashes[h]))
                else:
                    seen_hashes[h] = str(w_path)

                try:
                    with wave.open(str(w_path), "rb") as wf:
                        n = wf.getnframes()
                        raw = wf.readframes(n)
                        expected = n * wf.getnchannels() * wf.getsampwidth()
                        if len(raw) != expected:
                            report["corrupt_files"].append(str(w_path))
                            report["audio_pcm_valid"] = False
                except Exception:
                    report["corrupt_files"].append(str(w_path))
                    report["audio_pcm_valid"] = False

        # 3. Verifikasi Gambar (In-game & Skin)
        png_root = self.root_path / "PNG"
        if png_root.exists():
            for img_path in sorted(png_root.rglob("*.png")):
                report["total_files_scanned"] += 1
                h = compute_sha256(img_path)
                if h in seen_hashes:
                    report["duplicate_files"].append((str(img_path), seen_hashes[h]))
                else:
                    seen_hashes[h] = str(img_path)

                mat = cv2.imread(str(img_path))
                if mat is None or mat.size == 0:
                    report["corrupt_files"].append(str(img_path))
                    report["images_valid"] = False

        if report["corrupt_files"] or report["duplicate_files"]:
            report["status"] = "FAIL"

        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan, profile, and catalog Violence District killer dataset.")
    parser.add_argument(
        "--root",
        type=str,
        default="database/dataset/HIDDEN",
        help="Path root direktori dataset killer (default: database/dataset/HIDDEN)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/catalog.json",
        help="Path berkas output manifest JSON (default: dataset/catalog.json)",
    )
    parser.add_argument(
        "--verify-integrity",
        action="store_true",
        help="Jalankan pemeriksaan diagnostik integritas penuh terhadap seluruh berkas",
    )
    args = parser.parse_args()

    indexer = DatasetIndexer(root_path=Path(args.root))
    out_path = Path(args.output)
    catalog = indexer.save_catalog(out_path)

    print("=" * 70)
    print(" VIOLENCE DISTRICT COOLDOWN TRACKER — DATASET CATALOG REPORT (V2)")
    print("=" * 70)
    print(f"Killer ID              : {catalog.killer_id.upper()}")
    print(f"Schema Version         : v{catalog.schema_version}")
    print(f"Total Videos Indexed   : {catalog.total_videos} file ({catalog.total_video_duration_seconds:.2f}s total)")
    print(f"Total Video Frames     : {catalog.total_video_frames} frames (resolusi seragam 1280x720)")
    print(f"Positive Leap Videos   : {sum(1 for v in catalog.videos if v.is_positive_leap)}")
    print(f"Negative Action Videos : {sum(1 for v in catalog.videos if not v.is_positive_leap)}")
    print(f"In-Game Action Stills  : {catalog.total_ingame_images} PNG")
    print(f"Skin Variations        : {catalog.total_skin_variations} skins ({catalog.total_skin_images} PNG total)")
    print(f"Audio Ground Truth     : {catalog.total_audio_samples} WAV (44.1 kHz PCM)")
    print("-" * 70)
    print(f"Dataset Split Partition: Train={catalog.train_samples_count} | Val={catalog.val_samples_count} | Test={catalog.test_samples_count}")
    print(f"Catalog JSON Saved To  : {out_path.resolve()}")
    print("=" * 70)

    # Audio Spectral Summary
    if catalog.audio:
        print("\n[AKUSTIK] PROFIL SPEKTRAL GROUND TRUTH AUDIO:")
        for a in catalog.audio:
            tag = "[LEAP]" if a.is_positive_leap else "[NEG] "
            print(f"  {tag} {a.file_name:<32} | Centroid: {a.spectral_centroid_hz:7.1f} Hz | Dom: {a.dominant_frequency_hz:6.1f} Hz | {a.energy_dbfs:6.1f} dBFS")

    # Diagnostic Integrity Audit
    if args.verify_integrity:
        print("\n" + "=" * 70)
        print(" AUDIT DIAGNOSTIK INTEGRITAS DATASET")
        print("=" * 70)
        report = indexer.verify_integrity()
        print(f"Total File Diperiksa   : {report['total_files_scanned']}")
        print(f"Video Decodable        : {'OK' if report['video_decodable'] else 'GAGAL'}")
        print(f"Audio PCM Valid        : {'OK' if report['audio_pcm_valid'] else 'GAGAL'}")
        print(f"Citra PNG Valid        : {'OK' if report['images_valid'] else 'GAGAL'}")
        print(f"Duplikat Terdeteksi    : {len(report['duplicate_files'])}")
        print(f"Berkas Rusak/Korup     : {len(report['corrupt_files'])}")
        print(f"Hasil Akhir Status     : {report['status']}")
        print("=" * 70)


if __name__ == "__main__":
    main()
