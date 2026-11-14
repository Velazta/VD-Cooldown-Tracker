"""Unit tests for Dataset Extractor v2 (tools/extract_v2.py)."""

from pathlib import Path
import json
import numpy as np
import cv2
import pytest

from tools.extract_v2 import (
    compute_dhash,
    hamming_distance,
    infer_skin_id,
    DatasetExtractorV2,
)


def test_dhash_and_hamming_distance():
    # Create synthetic solid image
    img1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    h1 = compute_dhash(img1)
    
    # Identical image must have distance 0
    assert hamming_distance(h1, h1) == 0

    # Image with sharp gradient
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    for col in range(100):
        img2[:, col] = col * 2
    h2 = compute_dhash(img2)
    
    # Gradient image differs significantly from solid image
    assert hamming_distance(h1, h2) > 0


def test_infer_skin_id():
    assert infer_skin_id("hidden1_leap_skill.mp4") == "skin_1"
    assert infer_skin_id("hidden2_mark_skill.mp4") == "skin_2"
    assert infer_skin_id("hidden3_leap_skill.mp4") == "skin_3"
    assert infer_skin_id("hidden_skin6_neg_map1_01.mp4") == "skin_6"
    assert infer_skin_id("hidden_chasing_skill.mp4") == "skin_base"


def test_crop_frame_exact_and_scaling(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "capture": {
            "roi": {"x": 100, "y": 50, "width": 800, "height": 400, "enabled": True}
        }
    }), encoding="utf-8")

    extractor = DatasetExtractorV2(
        config_path=cfg_file,
        splits_path=tmp_path / "splits.json",
        temporal_path=tmp_path / "temporal.json",
        video_dir=tmp_path / "videos",
        output_dir=tmp_path / "out",
    )

    # 1. Exact match (1920x1032)
    frame_exact = np.zeros((1032, 1920, 3), dtype=np.uint8)
    cropped_exact = extractor.crop_frame(frame_exact, ref_width=1920, ref_height=1032)
    assert cropped_exact.shape == (400, 800, 3)

    # 2. Scaled down frame (960x516 -> half size)
    frame_half = np.zeros((516, 960, 3), dtype=np.uint8)
    cropped_half = extractor.crop_frame(frame_half, ref_width=1920, ref_height=1032)
    assert cropped_half.shape[0] == 200
    assert cropped_half.shape[1] == 400


def test_skill_windows_and_sampling(tmp_path: Path):
    temp_file = tmp_path / "temporal.json"
    temp_file.write_text(json.dumps({
        "videos": {
            "test_video.mp4": {
                "events": [
                    {"ability": "leap", "cast_start_frame": 30}
                ]
            }
        }
    }), encoding="utf-8")

    extractor = DatasetExtractorV2(
        config_path=tmp_path / "config.json",
        splits_path=tmp_path / "splits.json",
        temporal_path=temp_file,
        video_dir=tmp_path / "videos",
        output_dir=tmp_path / "out",
        window_seconds=1.0,
    )

    windows = extractor.get_skill_windows("test_video.mp4", fps=30.0)
    assert len(windows) == 1
    # 30 fps * 1.0s = 30 frames window -> [0, 60]
    assert windows[0][0] == 0
    assert windows[0][1] == 60
    assert windows[0][2] == "leap"

    in_skill, ability = extractor.is_in_skill_window(25, windows)
    assert in_skill is True
    assert ability == "leap"

    in_skill_far, _ = extractor.is_in_skill_window(100, windows)
    assert in_skill_far is False


def test_extract_video_end_to_end(tmp_path: Path):
    # Create small synthetic test video (10 frames)
    vid_path = tmp_path / "synth_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(vid_path), fourcc, 10.0, (640, 360))
    for i in range(10):
        # Vary pixels to avoid deduplication
        f = np.full((360, 640, 3), i * 25, dtype=np.uint8)
        vw.write(f)
    vw.release()

    out_dir = tmp_path / "yolo_out"
    extractor = DatasetExtractorV2(
        config_path=tmp_path / "dummy_cfg.json",
        splits_path=tmp_path / "dummy_splits.json",
        temporal_path=tmp_path / "dummy_temp.json",
        video_dir=tmp_path,
        output_dir=out_dir,
        negative_fps=10.0,
        dhash_threshold=0,
    )

    records = extractor.extract_video(vid_path, split="train")
    assert len(records) > 0

    # Verify Ultralytics paths exist
    first = records[0]
    img_file = out_dir / first.image_relpath
    lbl_file = out_dir / first.label_relpath

    assert img_file.exists()
    assert lbl_file.exists()
    # Confirm path replacement rule: images -> labels
    assert first.image_relpath.replace("images", "labels").replace(".jpg", ".txt") == first.label_relpath
