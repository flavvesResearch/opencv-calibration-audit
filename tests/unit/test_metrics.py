"""Geometry, image-quality, coverage, duplicate, and RMSE tests."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from calibration_audit import AuditPolicy, ImageMetrics, PatternSpec
from calibration_audit.calibration import reprojection_stats
from calibration_audit.metrics import (
    board_geometry,
    coverage_metrics,
    exposure_metrics,
    is_duplicate_pose,
    sharpness_metrics,
)


def grid_corners(cols: int = 3, rows: int = 2) -> np.ndarray:
    return np.asarray(
        [[20.0 + x * 30.0, 10.0 + y * 40.0] for y in range(rows) for x in range(cols)],
        dtype=np.float32,
    )


def test_board_geometry_values_and_bad_count() -> None:
    pattern = PatternSpec(cols=3, rows=2, square_size=1)
    result = board_geometry(grid_corners(), pattern, (100, 80))
    assert result["board_center"] == pytest.approx((0.5, 0.375))
    assert result["board_area_ratio"] == pytest.approx(0.30)
    assert result["rotation_degrees"] == pytest.approx(0)
    assert result["horizontal_perspective"] == pytest.approx(0)
    with pytest.raises(ValueError, match="Expected 6"):
        board_geometry(grid_corners()[:-1], pattern, (100, 80))


def test_exposure_and_blur_metric_directions() -> None:
    pattern = PatternSpec(cols=3, rows=2, square_size=1)
    sharp = np.zeros((80, 100), dtype=np.uint8)
    sharp[:, ::4] = 255
    blurred = cv2.GaussianBlur(sharp, (15, 15), 4)
    sharp_values = sharpness_metrics(sharp, grid_corners(), pattern)
    blurred_values = sharpness_metrics(blurred, grid_corners(), pattern)
    assert sharp_values[0] > blurred_values[0]
    assert sharp_values[1] > blurred_values[1]
    mean, black, white = exposure_metrics(np.asarray([[0, 255]], dtype=np.uint8))
    assert mean == 127.5
    assert black == 0.5
    assert white == 0.5


def test_coverage_clamps_edges_and_counts_density() -> None:
    metrics = [
        ImageMetrics(file_size=1, board_center=(0.0, 0.0)),
        ImageMetrics(file_size=1, board_center=(1.0, 1.0)),
        ImageMetrics(file_size=1, board_center=(0.5, 0.5)),
    ]
    occupancy, ratio, density = coverage_metrics(
        metrics,
        cols=2,
        rows=2,
        corners=[[[0, 0], [99, 99]]],
        image_size=(100, 100),
    )
    assert occupancy == [[1, 0], [0, 2]]
    assert ratio == 0.5
    assert density == [[1, 0], [0, 1]]


def pose(rotation: float, sharpness: float = 10) -> ImageMetrics:
    return ImageMetrics(
        file_size=1,
        board_center=(0.5, 0.5),
        board_area_ratio=0.2,
        rotation_degrees=rotation,
        horizontal_perspective=0.1,
        vertical_perspective=0.1,
        board_sharpness=sharpness,
    )


def test_duplicate_pose_handles_angle_wrap_and_missing_metrics() -> None:
    policy = AuditPolicy()
    assert is_duplicate_pose(pose(179), pose(-179), policy)
    far = pose(20)
    far.board_center = (0.9, 0.9)
    assert not is_duplicate_pose(pose(0), far, policy)
    assert not is_duplicate_pose(pose(0), ImageMetrics(file_size=1), policy)


def test_reprojection_rmse_formula_and_validation() -> None:
    observed = np.asarray([[0, 0], [0, 0]], dtype=np.float32)
    projected = np.asarray([[3, 4], [0, 0]], dtype=np.float32)
    result = reprojection_stats(observed, projected)
    assert result.rmse_px == pytest.approx(np.sqrt(12.5))
    assert result.mean_px == 2.5
    assert result.median_px == 2.5
    assert result.max_px == 5
    with pytest.raises(ValueError):
        reprojection_stats(np.empty((0, 2), np.float32), np.empty((0, 2), np.float32))
