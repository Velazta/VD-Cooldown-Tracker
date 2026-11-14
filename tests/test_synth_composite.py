"""Unit tests for Synthetic Foreground-Background Compositor (tools/synth_composite.py)."""

from pathlib import Path
import cv2
import numpy as np
import pytest

from tools.synth_composite import (
    extract_foreground_and_mask,
    apply_highlight_aura,
    SyntheticCompositor,
)


def test_extract_foreground_and_mask():
    # 4-channel image with custom alpha
    rgba = np.full((100, 80, 4), 200, dtype=np.uint8)
    rgba[:, :, 3] = 0
    rgba[20:60, 20:60, 3] = 255

    bgr, mask = extract_foreground_and_mask(rgba)
    assert bgr.shape == (100, 80, 3)
    assert mask.shape == (100, 80)
    assert mask[30, 30] == 255
    assert mask[5, 5] == 0


def test_apply_highlight_aura():
    fg = np.full((50, 50, 3), 100, dtype=np.uint8)
    mask = np.zeros((50, 50), dtype=np.uint8)
    mask[15:35, 15:35] = 255

    aura_fg, aura_mask = apply_highlight_aura(fg, mask, aura_color=(0, 255, 0), thickness=2)
    assert aura_fg.shape == (50, 50, 3)
    # Dilated mask must be larger than original
    assert np.count_nonzero(aura_mask) > np.count_nonzero(mask)


def test_reject_val_or_test_splits(tmp_path: Path):
    compositor = SyntheticCompositor(dataset_dir=tmp_path)
    with pytest.raises(ValueError, match="strictly forbidden in 'val'"):
        compositor.generate_synthetic_samples(count=5, split="val")
    with pytest.raises(ValueError, match="strictly forbidden in 'test'"):
        compositor.generate_synthetic_samples(count=5, split="test")


def test_synthetic_generation_mini_integration(tmp_path: Path):
    ds_dir = tmp_path / "yolo"
    train_img_dir = ds_dir / "images" / "train"
    train_lbl_dir = ds_dir / "labels" / "train"
    train_img_dir.mkdir(parents=True)
    train_lbl_dir.mkdir(parents=True)

    # Create dummy background
    bg = np.full((400, 800, 3), 50, dtype=np.uint8)
    cv2.imwrite(str(train_img_dir / "bg_frame_01.jpg"), bg)
    (train_lbl_dir / "bg_frame_01.txt").write_text("", encoding="utf-8")

    # Create dummy cutouts
    k_dir = tmp_path / "killer_cutouts"
    s_dir = tmp_path / "survivor_cutouts"
    k_dir.mkdir()
    s_dir.mkdir()

    k_img = np.full((60, 40, 3), 180, dtype=np.uint8)
    cv2.imwrite(str(k_dir / "crop_killer.jpg"), k_img)

    s_img = np.full((80, 50, 3), 220, dtype=np.uint8)
    cv2.imwrite(str(s_dir / "crop_survivor.png"), s_img)

    compositor = SyntheticCompositor(
        dataset_dir=ds_dir,
        killer_cutouts_dir=k_dir,
        survivor_cutouts_dir=s_dir,
        references_dir=tmp_path / "none",
        seed=123,
    )

    records = compositor.generate_synthetic_samples(count=3, split="train", clean_existing=True)
    assert len(records) == 3

    for r in records:
        stem = r["frame_id"]
        img_p = train_img_dir / f"{stem}.jpg"
        lbl_p = train_lbl_dir / f"{stem}.txt"
        assert img_p.exists()
        assert lbl_p.exists()

        lbl_content = lbl_p.read_text(encoding="utf-8").strip()
        assert len(lbl_content) > 0  # Must contain at least 1 box
        for line in lbl_content.splitlines():
            tokens = line.split()
            assert len(tokens) == 5
            cid = int(tokens[0])
            assert cid in (0, 1)
            coords = list(map(float, tokens[1:]))
            for c in coords:
                assert 0.0 <= c <= 1.0
