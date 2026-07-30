"""OpenCV checkerboard detectors."""

from __future__ import annotations

from time import perf_counter

import cv2
import numpy as np
import numpy.typing as npt

from ..models import PatternSpec


def detect_checkerboard(
    gray: npt.NDArray[np.uint8],
    pattern: PatternSpec,
    *,
    fallback: bool = True,
) -> tuple[bool, npt.NDArray[np.float32] | None, str | None, float]:
    """Detect all inner corners using SB and optionally the classic detector."""

    started = perf_counter()
    flags = cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_EXHAUSTIVE
    try:
        found, corners = cv2.findChessboardCornersSB(gray, pattern.pattern_size, flags=flags)
    except cv2.error:
        found, corners = False, None
    method: str | None = "findChessboardCornersSB" if found else None

    if not found and fallback:
        classic_flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
        try:
            found, classic = cv2.findChessboardCorners(
                gray, pattern.pattern_size, flags=classic_flags
            )
        except cv2.error:
            found, classic = False, None
        if found and classic is not None:
            criteria = (
                cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
                30,
                0.001,
            )
            corners = cv2.cornerSubPix(gray, classic, (11, 11), (-1, -1), criteria)
            method = "findChessboardCorners+cornerSubPix"

    duration_ms = (perf_counter() - started) * 1000.0
    if not found or corners is None:
        return False, None, None, duration_ms
    flat = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
    if flat.shape[0] != pattern.cols * pattern.rows:
        return False, flat, method, duration_ms
    return True, flat, method, duration_ms
