"""OpenCV pinhole camera calibration."""

from __future__ import annotations

import cv2
import numpy as np
import numpy.typing as npt

from ..exceptions import CalibrationFailedError
from ..models import CalibrationResult, PatternSpec, ReprojectionStats


def object_points(pattern: PatternSpec) -> npt.NDArray[np.float32]:
    """Create planar object points in metres."""

    points = np.zeros((pattern.rows * pattern.cols, 3), dtype=np.float32)
    points[:, :2] = np.mgrid[0 : pattern.cols, 0 : pattern.rows].T.reshape(-1, 2)
    points[:, :2] *= pattern.square_size_metres
    return points


def reprojection_stats(
    observed: npt.NDArray[np.float32],
    projected: npt.NDArray[np.float32],
) -> ReprojectionStats:
    """Calculate Euclidean point errors and RMSE=sqrt(mean(dx²+dy²))."""

    first = np.asarray(observed, dtype=np.float64).reshape(-1, 2)
    second = np.asarray(projected, dtype=np.float64).reshape(-1, 2)
    if first.shape != second.shape or first.shape[0] == 0:
        raise ValueError("Observed and projected points must have equal non-empty shapes")
    differences = second - first
    squared = np.sum(differences * differences, axis=1)
    distances = np.sqrt(squared)
    return ReprojectionStats(
        rmse_px=float(np.sqrt(np.mean(squared))),
        mean_px=float(np.mean(distances)),
        median_px=float(np.median(distances)),
        max_px=float(np.max(distances)),
        point_count=int(first.shape[0]),
    )


def calibrate(
    corners: list[npt.NDArray[np.float32]],
    pattern: PatternSpec,
    image_size: tuple[int, int],
    *,
    flags: int = 0,
) -> tuple[CalibrationResult, list[ReprojectionStats]]:
    """Calibrate from all accepted pre-calibration views without pruning."""

    points = object_points(pattern)
    object_sets = [points.copy() for _ in corners]
    image_sets = [item.reshape(-1, 1, 2).astype(np.float32) for item in corners]
    try:
        rms, matrix, distortion, rvecs, tvecs = cv2.calibrateCamera(
            object_sets, image_sets, image_size, None, None, flags=flags
        )
    except cv2.error as exc:
        raise CalibrationFailedError(f"OpenCV camera calibration failed: {exc}") from exc
    if not np.isfinite(rms) or not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(distortion)):
        raise CalibrationFailedError("OpenCV returned non-finite calibration parameters")

    per_view: list[ReprojectionStats] = []
    for observed, rvec, tvec in zip(image_sets, rvecs, tvecs):
        projected, _ = cv2.projectPoints(points, rvec, tvec, matrix, distortion)
        per_view.append(
            reprojection_stats(observed, np.asarray(projected, dtype=np.float32))
        )
    mean_rmse = float(np.mean([item.rmse_px for item in per_view]))
    result = CalibrationResult(
        image_size=image_size,
        opencv_rms=float(rms),
        camera_matrix=np.asarray(matrix, dtype=float).tolist(),
        distortion_coefficients=np.asarray(distortion, dtype=float).reshape(-1).tolist(),
        rotation_vectors=[np.asarray(value, dtype=float).reshape(-1).tolist() for value in rvecs],
        translation_vectors=[np.asarray(value, dtype=float).reshape(-1).tolist() for value in tvecs],
        calibration_flags=flags,
        mean_per_view_rmse_px=mean_rmse,
    )
    return result, per_view
