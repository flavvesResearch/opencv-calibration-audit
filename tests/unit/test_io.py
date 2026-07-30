"""Image discovery and loading failure tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from calibration_audit.exceptions import DatasetValidationError
from calibration_audit.io import discover_images, load_image


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
        loaded, gray, actual_channels = load_image(path, max_file_size_bytes=1_000_000)
        assert loaded.shape == image.shape
        assert gray.shape == (10, 12)
        assert actual_channels == channels
    corrupt = tmp_path / "bad.png"
    corrupt.write_bytes(b"not an image")
    with pytest.raises(DatasetValidationError, match="decode"):
        load_image(corrupt, max_file_size_bytes=100)
    with pytest.raises(DatasetValidationError, match="exceeds"):
        load_image(corrupt, max_file_size_bytes=1)
