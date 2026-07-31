"""Image discovery and loading failure tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from conftest import checkerboard

from calibration_audit.detection import detect_checkerboard
from calibration_audit.exceptions import DatasetValidationError
from calibration_audit.io import discover_images, load_image
from calibration_audit.metrics import exposure_metrics
from calibration_audit.models import PatternSpec


def test_discovery_is_sorted_and_respects_recursive(tmp_path: Path) -> None:
    (tmp_path / "b.PNG").write_bytes(b"x")
    (tmp_path / "A.jpg").write_bytes(b"x")
    (tmp_path / "ignored.txt").write_text("x")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.webp").write_bytes(b"x")
    assert [path.name for path in discover_images(tmp_path)] == ["A.jpg", "b.PNG"]
    assert [path.name for path in discover_images(tmp_path, recursive=True)] == [
        "A.jpg",
        "b.PNG",
        "c.webp",
    ]


def test_discovery_rejects_bad_inputs(tmp_path: Path) -> None:
    with pytest.raises(DatasetValidationError, match="does not exist"):
        discover_images(tmp_path / "missing")
    file_path = tmp_path / "file"
    file_path.write_text("x")
    with pytest.raises(DatasetValidationError, match="not a directory"):
        discover_images(file_path)
    with pytest.raises(DatasetValidationError, match="No supported images"):
        discover_images(tmp_path)


def test_recursive_discovery_ignores_symlink_outside_tree(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-audit-image.png"
    outside.write_bytes(b"x")
    link = tmp_path / "escape.png"
    try:
        link.symlink_to(outside)
        with pytest.raises(DatasetValidationError, match="No supported images"):
            discover_images(tmp_path, recursive=True)
    finally:
        outside.unlink(missing_ok=True)


def test_load_grayscale_color_alpha_and_corrupt(tmp_path: Path) -> None:
    images = [
        np.zeros((10, 12), dtype=np.uint8),
        np.zeros((10, 12, 3), dtype=np.uint8),
        np.zeros((10, 12, 4), dtype=np.uint8),
    ]
    for channels, image in zip((1, 3, 4), images):
        path = tmp_path / f"{channels}.png"
        assert cv2.imwrite(str(path), image)
        loaded, gray, actual_channels, original_dtype, bit_depth = load_image(
            path, max_file_size_bytes=1_000_000
        )
        assert loaded.shape == image.shape
        assert gray.shape == (10, 12)
        assert actual_channels == channels
        assert original_dtype == "uint8"
        assert bit_depth == 8
    corrupt = tmp_path / "bad.png"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(DatasetValidationError, match="decode"):
        load_image(corrupt, max_file_size_bytes=100)
    with pytest.raises(DatasetValidationError, match="exceeds"):
        load_image(corrupt, max_file_size_bytes=1)


def test_uint16_tiff_uses_fixed_range_normalization_for_analysis(tmp_path: Path) -> None:
    image = checkerboard().astype(np.uint16) * 257
    path = tmp_path / "checkerboard-16.tiff"
    assert cv2.imwrite(str(path), image)
    loaded, gray, channels, original_dtype, bit_depth = load_image(
        path, max_file_size_bytes=5_000_000
    )
    assert loaded.dtype == np.uint8
    assert gray.dtype == np.uint8
    assert channels == 1
    assert original_dtype == "uint16"
    assert bit_depth == 16
    assert exposure_metrics(gray) == pytest.approx((127.5, 0.5, 0.5))
    found, corners, _, _ = detect_checkerboard(
        gray,
        PatternSpec(cols=9, rows=6, square_size=1),
    )
    assert found
    assert corners is not None


@pytest.mark.parametrize("dtype", [np.int16, np.float32])
def test_signed_and_float_tiff_are_rejected(tmp_path: Path, dtype: np.dtype) -> None:
    path = tmp_path / f"unsupported-{np.dtype(dtype).name}.tiff"
    assert cv2.imwrite(str(path), np.ones((10, 12), dtype=dtype))
    with pytest.raises(DatasetValidationError, match="Unsupported image dtype"):
        load_image(path, max_file_size_bytes=1_000_000)
