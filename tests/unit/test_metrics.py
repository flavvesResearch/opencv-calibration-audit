"""Geometry, image-quality, coverage, duplicate, and RMSE tests."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from calibration_audit import AuditPolicy, ImageAuditResult, ImageMetrics, PatternSpec
from calibration_audit.calibration import reprojection_stats
from calibration_audit.metrics import (
    board_geometry,
    coverage_metrics,
    exposure_metrics,
    is_duplicate_pose,
    sharpness_metrics,
)
from calibration_audit.pipeline import _diversity


def grid_corners(cols: int = 3, rows: int = 2) -> np.ndarray:
    return np.asarray(
        [[20.0 + x * 30.0, 10.0 + y * 40.0] for y in range(rows) for x in range(cols)],
        dtype=np.float32,
    )


def test_board_geometry_values_and_bad_count() -> None:
    pattern = PatternSpec(cols=3, rows=2, square_size=1)
    result = board_geometry(grid_corners(), pattern, (100, 80))
    assert result["board_center"] == pytest.approx((0.5, 0.375))
    assert result["rotation_degrees"] == pytest.approx(0)
    assert result["horizontal_perspective"] == pytest.approx(0)
    with pytest.raises(ValueError, match="Expected 6"):
        board_geometry(grid_corners()[:-1], pattern, (100, 80))


def test_physical_board_boundary_area_and_border_distance() -> None:
    pattern = PatternSpec(cols=3, rows=2, square_size=1)
    corners = np.asarray(
        [[30.0 + x * 20.0, 30.0 + y * 20.0] for y in range(2) for x in range(3)],
        dtype=np.float32,
    )
    result = board_geometry(corners, pattern, (100, 100))
    np.testing.assert_allclose(
        result["board_boundary"],
        [[10.0, 10.0], [90.0, 10.0], [90.0, 70.0], [10.0, 70.0]],
        atol=1e-4,
    )
    assert result["board_area_ratio"] == pytest.approx(0.48)
    assert result["border_distance_ratio"] == pytest.approx(0.09)


def test_physical_boundary_detects_clipping_with_visible_inner_corners() -> None:
    pattern = PatternSpec(cols=3, rows=2, square_size=1)
    corners = np.asarray(
        [[5.0 + x * 20.0, 25.0 + y * 20.0] for y in range(2) for x in range(3)],
        dtype=np.float32,
    )
    result = board_geometry(corners, pattern, (100, 100))
    assert result["border_distance_ratio"] < 0
    assert min(point[0] for point in result["board_boundary"]) < 0
    assert np.isfinite(np.asarray(result["board_boundary"])).all()


def test_physical_boundary_is_stable_under_perspective() -> None:
    pattern = PatternSpec(cols=4, rows=3, square_size=1)
    logical_boundary = np.float32([[-1, -1], [4, -1], [4, 3], [-1, 3]])
    image_boundary = np.float32([[12, 18], [175, 9], [161, 132], [25, 141]])
    transform = cv2.getPerspectiveTransform(logical_boundary, image_boundary)
    logical_corners = np.float32(
        [[x, y] for y in range(pattern.rows) for x in range(pattern.cols)]
    ).reshape(-1, 1, 2)
    corners = cv2.perspectiveTransform(logical_corners, transform).reshape(-1, 2)
    result = board_geometry(corners, pattern, (200, 160))
    np.testing.assert_allclose(result["board_boundary"], image_boundary, atol=1e-3)
    assert result["board_area_ratio"] == pytest.approx(
        cv2.contourArea(image_boundary) / (200 * 160), rel=1e-4
    )


@pytest.mark.parametrize(
    ("angles", "expected"),
    [
        ([179.0, -179.0], 2.0),
        ([-10.0, 0.0, 10.0], 20.0),
        ([0.0], 0.0),
        ([0.0, 90.0, 180.0, -90.0], 270.0),
    ],
)
def test_rotation_diversity_uses_smallest_circular_covering_arc(
    angles: list[float], expected: float
) -> None:
    images = [
        ImageAuditResult(
            relative_path=f"{index}.png",
            metrics=ImageMetrics(
                file_size=1,
                board_area_ratio=0.2,
                rotation_degrees=angle,
            ),
        )
        for index, angle in enumerate(angles)
    ]
    assert _diversity(images)[5] == pytest.approx(expected)


def test_perspective_metrics_preserve_tilt_direction() -> None:
    pattern = PatternSpec(cols=3, rows=2, square_size=1)
    horizontal_a = np.float32([[30, 20], [70, 20], [20, 70], [80, 70]])
    horizontal_b = np.float32([[20, 20], [80, 20], [30, 70], [70, 70]])
    vertical_a = np.float32([[20, 30], [70, 20], [70, 80], [20, 70]])
    vertical_b = np.float32([[20, 20], [70, 30], [70, 70], [20, 80]])

    def grid_from_quad(quad: np.ndarray) -> np.ndarray:
        logical = np.float32([[0, 0], [2, 0], [2, 1], [0, 1]])
        transform = cv2.getPerspectiveTransform(logical, quad)
        grid = np.float32([[x, y] for y in range(2) for x in range(3)]).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(grid, transform).reshape(-1, 2)

    h_a = board_geometry(grid_from_quad(horizontal_a), pattern, (100, 100))
    h_b = board_geometry(grid_from_quad(horizontal_b), pattern, (100, 100))
    v_a = board_geometry(grid_from_quad(vertical_a), pattern, (100, 100))
    v_b = board_geometry(grid_from_quad(vertical_b), pattern, (100, 100))
    assert h_a["horizontal_perspective"] == pytest.approx(
        -h_b["horizontal_perspective"], abs=1e-6
    )
    assert h_a["horizontal_perspective"] != 0
    assert v_a["vertical_perspective"] == pytest.approx(
        -v_b["vertical_perspective"], abs=1e-6
    )
    assert v_a["vertical_perspective"] != 0


def test_opposite_perspective_tilts_are_not_duplicates() -> None:
    policy = AuditPolicy()
    first = pose(0)
    second = pose(0)
    first.horizontal_perspective = -0.1
    second.horizontal_perspective = 0.1
    assert not is_duplicate_pose(first, second, policy)


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
