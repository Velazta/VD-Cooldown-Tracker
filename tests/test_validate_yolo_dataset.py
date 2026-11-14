"""Unit tests for YOLO Dataset Validator (tools/validate_yolo_dataset.py)."""

from pathlib import Path
import pytest
from tools.validate_yolo_dataset import calculate_box_iou, validate_yolo_dataset


def test_calculate_box_iou():
    # Exactly identical boxes
    b1 = (0.5, 0.5, 0.2, 0.2)
    assert pytest.approx(calculate_box_iou(b1, b1), 0.001) == 1.0

    # Completely disjoint boxes
    b2 = (0.1, 0.1, 0.05, 0.05)
    assert calculate_box_iou(b1, b2) == 0.0

    # Partial overlap
    b3 = (0.55, 0.5, 0.2, 0.2)
    iou = calculate_box_iou(b1, b3)
    assert 0.0 < iou < 1.0


def test_validate_clean_dataset(tmp_path: Path):
    ds_dir = tmp_path / "yolo"
    img_dir = ds_dir / "images" / "train"
    lbl_dir = ds_dir / "labels" / "train"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)

    # 1. Image with valid box
    (img_dir / "vidA_f00010.jpg").write_bytes(b"dummy")
    (lbl_dir / "vidA_f00010.txt").write_text("0 0.5 0.5 0.2 0.3\n1 0.2 0.2 0.1 0.1\n", encoding="utf-8")

    # 2. Image with empty background
    (img_dir / "vidA_f00020.jpg").write_bytes(b"dummy")
    (lbl_dir / "vidA_f00020.txt").write_text("", encoding="utf-8")

    data_yaml = tmp_path / "training" / "data.yaml"
    is_valid, errors, stats = validate_yolo_dataset(
        dataset_dir=ds_dir,
        data_yaml_out=data_yaml,
    )

    assert is_valid is True
    assert len(errors) == 0
    assert stats["total_images"] == 2
    assert stats["total_labels"] == 2
    assert stats["class_counts"][0] == 1
    assert stats["class_counts"][1] == 1
    assert stats["background_images"] == 1
    assert data_yaml.exists()


def test_validate_detects_corruptions(tmp_path: Path):
    ds_dir = tmp_path / "yolo_bad"
    img_dir = ds_dir / "images" / "train"
    lbl_dir = ds_dir / "labels" / "train"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)

    # Missing label
    (img_dir / "vid1_f00001.jpg").write_bytes(b"dummy")

    # Invalid class ID (e.g. legacy class 3)
    (img_dir / "vid1_f00002.jpg").write_bytes(b"dummy")
    (lbl_dir / "vid1_f00002.txt").write_text("3 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    # Out of bounds coordinates
    (img_dir / "vid1_f00003.jpg").write_bytes(b"dummy")
    (lbl_dir / "vid1_f00003.txt").write_text("0 1.5 0.5 0.2 0.2\n", encoding="utf-8")

    is_valid, errors, stats = validate_yolo_dataset(dataset_dir=ds_dir)

    assert is_valid is False
    assert any("Missing label file" in e for e in errors)
    assert any("Invalid class ID 3" in e for e in errors)
    assert any("out of bounds" in e for e in errors)


def test_validate_detects_split_leakage(tmp_path: Path):
    ds_dir = tmp_path / "yolo_leak"
    for split in ["train", "val"]:
        (ds_dir / "images" / split).mkdir(parents=True)
        (ds_dir / "labels" / split).mkdir(parents=True)

    # Same video stem "vidLeaked" in both train and val
    (ds_dir / "images" / "train" / "vidLeaked_f00001.jpg").write_bytes(b"dummy")
    (ds_dir / "labels" / "train" / "vidLeaked_f00001.txt").write_text("", encoding="utf-8")

    (ds_dir / "images" / "val" / "vidLeaked_f00002.jpg").write_bytes(b"dummy")
    (ds_dir / "labels" / "val" / "vidLeaked_f00002.txt").write_text("", encoding="utf-8")

    is_valid, errors, stats = validate_yolo_dataset(dataset_dir=ds_dir)

    assert is_valid is False
    assert any("Video leakage detected" in e for e in errors)
