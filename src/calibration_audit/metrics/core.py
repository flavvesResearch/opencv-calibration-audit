"""Metric calculations without policy decisions."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TypedDict

import cv2
import numpy as np
import numpy.typing as npt

from ..config import AuditPolicy
from ..models import ImageMetrics, PatternSpec


class GeometryMetrics(TypedDict):
    board_center: tuple[float, float]
    board_boundary: list[list[float]]
    board_area_ratio: float
    rotation_degrees: float
    horizontal_perspective: float
    vertical_perspective: float
    border_distance_ratio: float


def _distance(first: npt.NDArray[np.float32], second: npt.NDArray[np.float32]) -> float:
    return float(np.linalg.norm(first - second))


def board_geometry(
    corners: npt.NDArray[np.float32],
    pattern: PatternSpec,
    image_size: tuple[int, int],
) -> GeometryMetrics:
    """Calculate geometry using an extrapolated physical checkerboard boundary.

    The detected grid consists of inner corners. A homography projects a
    boundary one square beyond each outer inner-corner row and column, matching
    the physical extent of a checkerboard with ``cols + 1`` by ``rows + 1``
    squares. The sharpness metric intentionally remains based on the
    conservative inner-corner hull.
    """

    width, height = image_size
    expected = pattern.cols * pattern.rows
    points = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
    if points.shape[0] != expected:
        raise ValueError(f"Expected {expected} corners, received {points.shape[0]}")
    quad = np.asarray(
        [
            points[0],
            points[pattern.cols - 1],
            points[-1],
            points[(pattern.rows - 1) * pattern.cols],
        ],
        dtype=np.float32,
    )
    logical_corners = np.asarray(
        [[x, y] for y in range(pattern.rows) for x in range(pattern.cols)],
        dtype=np.float32,
    )
    homography, _ = cv2.findHomography(logical_corners, points, method=0)
    if homography is None or not np.isfinite(homography).all():
        raise ValueError("Could not estimate a finite physical board boundary")
    logical_boundary = np.asarray(
        [[-1.0, -1.0], [pattern.cols, -1.0], [pattern.cols, pattern.rows], [-1.0, pattern.rows]],
        dtype=np.float32,
    ).reshape(-1, 1, 2)
    boundary = cv2.perspectiveTransform(logical_boundary, homography).reshape(-1, 2)
    if not np.isfinite(boundary).all():
        raise ValueError("Estimated physical board boundary is not finite")
    center = np.mean(quad, axis=0)
    area = abs(float(cv2.contourArea(boundary))) / float(width * height)
    top = _distance(quad[0], quad[1])
    bottom = _distance(quad[3], quad[2])
    left = _distance(quad[0], quad[3])
    right = _distance(quad[1], quad[2])
    horizontal = (top - bottom) / max(top, bottom, 1e-12)
    vertical = (left - right) / max(left, right, 1e-12)
    angle = math.degrees(math.atan2(float(quad[1, 1] - quad[0, 1]), float(quad[1, 0] - quad[0, 0])))
    border = min(
        float(np.min(boundary[:, 0])) / width,
        float(np.min(boundary[:, 1])) / height,
        float(width - 1 - np.max(boundary[:, 0])) / width,
        float(height - 1 - np.max(boundary[:, 1])) / height,
    )
    return {
        "board_center": (float(center[0] / width), float(center[1] / height)),
        "board_boundary": boundary.astype(float).tolist(),
        "board_area_ratio": area,
        "rotation_degrees": angle,
        "horizontal_perspective": horizontal,
        "vertical_perspective": vertical,
        "border_distance_ratio": border,
    }


def sharpness_metrics(
    gray: npt.NDArray[np.uint8],
    corners: npt.NDArray[np.float32],
    pattern: PatternSpec,
) -> tuple[float, float]:
    """Return variance of Laplacian globally and inside the board quadrilateral."""

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    global_value = float(laplacian.var())
    points = corners.reshape(-1, 2)
    quad = np.asarray(
        [
            points[0],
            points[pattern.cols - 1],
            points[-1],
            points[(pattern.rows - 1) * pattern.cols],
        ],
        dtype=np.int32,
    )
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, quad, 255)
    values = laplacian[mask > 0]
    board_value = float(values.var()) if values.size else global_value
    return global_value, board_value


def exposure_metrics(gray: npt.NDArray[np.uint8]) -> tuple[float, float, float]:
    """Return mean intensity and near-black/near-white pixel ratios."""

    return (
        float(np.mean(gray)),
        float(np.mean(gray <= 5)),
        float(np.mean(gray >= 250)),
    )


def coverage_metrics(
    metrics: list[ImageMetrics],
    *,
    cols: int = 4,
    rows: int = 3,
    corners: list[list[list[float]]] | None = None,
    image_size: tuple[int, int] | None = None,
) -> tuple[list[list[int]], float, list[list[int]]]:
    """Calculate board-center occupancy and optional corner observation density."""

    occupancy = np.zeros((rows, cols), dtype=np.int32)
    density = np.zeros((rows, cols), dtype=np.int32)
    for metric in metrics:
        if metric.board_center is None:
            continue
        x, y = metric.board_center
        col = min(cols - 1, max(0, int(x * cols)))
        row = min(rows - 1, max(0, int(y * rows)))
        occupancy[row, col] += 1
    if corners is not None and image_size is not None:
        width, height = image_size
        for view in corners:
            for x, y in view:
                col = min(cols - 1, max(0, int((x / width) * cols)))
                row = min(rows - 1, max(0, int((y / height) * rows)))
                density[row, col] += 1
    ratio = float(np.count_nonzero(occupancy) / occupancy.size)
    return occupancy.tolist(), ratio, density.tolist()


def _angle_distance(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def circular_range_degrees(angles: Sequence[float]) -> float:
    """Return the smallest circular arc containing all angles.

    Inputs are normalized to ``[-180, 180)``. For evenly distributed cardinal
    orientations (0, 90, 180, -90), the smallest covering arc is 270 degrees.
    """

    if not angles:
        raise ValueError("At least one angle is required")
    normalized = sorted((angle + 180.0) % 360.0 for angle in angles)
    if len(normalized) == 1:
        return 0.0
    gaps = [
        normalized[index + 1] - normalized[index]
        for index in range(len(normalized) - 1)
    ]
    gaps.append(normalized[0] + 360.0 - normalized[-1])
    return 360.0 - max(gaps)


def is_duplicate_pose(first: ImageMetrics, second: ImageMetrics, policy: AuditPolicy) -> bool:
    """Compare normalized pose properties using documented component thresholds."""

    required = (
        first.board_center,
        second.board_center,
        first.board_area_ratio,
        second.board_area_ratio,
        first.rotation_degrees,
        second.rotation_degrees,
        first.horizontal_perspective,
        second.horizontal_perspective,
        first.vertical_perspective,
        second.vertical_perspective,
    )
    if any(value is None for value in required):
        return False
    assert first.board_center is not None and second.board_center is not None
    assert first.board_area_ratio is not None and second.board_area_ratio is not None
    assert first.rotation_degrees is not None and second.rotation_degrees is not None
    assert first.horizontal_perspective is not None
    assert second.horizontal_perspective is not None
    assert first.vertical_perspective is not None
    assert second.vertical_perspective is not None
    center_distance = math.hypot(
        first.board_center[0] - second.board_center[0],
        first.board_center[1] - second.board_center[1],
    )
    area_distance = abs(math.log(first.board_area_ratio) - math.log(second.board_area_ratio))
    perspective_distance = math.hypot(
        first.horizontal_perspective - second.horizontal_perspective,
        first.vertical_perspective - second.vertical_perspective,
    )
    return (
        center_distance <= policy.duplicate_center_distance
        and area_distance <= policy.duplicate_log_area_distance
        and _angle_distance(first.rotation_degrees, second.rotation_degrees)
        <= policy.duplicate_rotation_degrees
        and perspective_distance <= policy.duplicate_perspective_distance
    )
