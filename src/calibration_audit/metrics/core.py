"""Metric calculations without policy decisions."""

from __future__ import annotations

import math
from typing import TypedDict

import cv2
import numpy as np
import numpy.typing as npt

from ..config import AuditPolicy
from ..models import ImageMetrics, PatternSpec


class GeometryMetrics(TypedDict):
    board_center: tuple[float, float]
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
    """Calculate normalized geometry from the four outermost inner corners."""

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
    center = np.mean(quad, axis=0)
    area = abs(float(cv2.contourArea(quad))) / float(width * height)
    top = _distance(quad[0], quad[1])
    bottom = _distance(quad[3], quad[2])
    left = _distance(quad[0], quad[3])
    right = _distance(quad[1], quad[2])
    horizontal = abs(top - bottom) / max(top, bottom, 1e-12)
    vertical = abs(left - right) / max(left, right, 1e-12)
    angle = math.degrees(math.atan2(float(quad[1, 1] - quad[0, 1]), float(quad[1, 0] - quad[0, 0])))
    border = min(
        float(np.min(quad[:, 0])) / width,
        float(np.min(quad[:, 1])) / height,
        float(width - 1 - np.max(quad[:, 0])) / width,
        float(height - 1 - np.max(quad[:, 1])) / height,
    )
    return {
        "board_center": (float(center[0] / width), float(center[1] / height)),
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
