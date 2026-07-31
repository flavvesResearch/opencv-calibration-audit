"""Integration coverage using redistributable real-camera OpenCV samples."""

from __future__ import annotations

import base64
from pathlib import Path

import cv2
import numpy as np

from calibration_audit import AuditConfig, PatternSpec, audit_dataset


def _decode_fixtures(destination: Path) -> list[Path]:
    fixture_root = Path(__file__).parents[1] / "fixtures" / "opencv-real"
    paths: list[Path] = []
    for encoded_path in sorted(fixture_root.glob("*.jpg.base64")):
        path = destination / encoded_path.name.removesuffix(".base64")
        path.write_bytes(base64.b64decode(encoded_path.read_text(encoding="ascii")))
        paths.append(path)
    return paths


def test_real_camera_dataset_decisions_and_calibration_sanity(tmp_path: Path) -> None:
    paths = _decode_fixtures(tmp_path)
    assert [path.name for path in paths] == ["left01.jpg", "left02.jpg", "left03.jpg"]

    first = cv2.imread(str(paths[0]), cv2.IMREAD_GRAYSCALE)
    second = cv2.imread(str(paths[1]), cv2.IMREAD_GRAYSCALE)
    assert first is not None and second is not None
    dark = np.asarray(first, dtype=np.float32) * 0.12
    assert cv2.imwrite(str(tmp_path / "dark-left01.png"), dark.astype(np.uint8))
    blurred = cv2.GaussianBlur(second, (31, 31), 7)
    assert cv2.imwrite(str(tmp_path / "blurred-left02.png"), blurred)

    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=3,
        min_board_area=0.01,
    )
    result = audit_dataset(tmp_path, config)

    originals = [image for image in result.images if image.relative_path.startswith("left")]
    assert len(originals) == 3
    assert all(image.detection_success for image in originals)
    assert all(image.state.value in {"ACCEPTED", "WARNING"} for image in originals)
    assert result.dataset_metrics.accepted_count == 3
    assert result.dataset_metrics.duplicate_count == 2
    assert any(
        reason.code.value == "EXPOSURE_TOO_DARK"
        for image in result.images
        if image.relative_path == "dark-left01.png"
        for reason in image.reasons
    )
    assert any(
        reason.code.value == "LOW_SHARPNESS"
        for image in result.images
        if image.relative_path == "blurred-left02.png"
        for reason in image.reasons
    )
    assert any(
        reason.code.value == "BOARD_CLIPPED_OR_NEAR_BORDER"
        for image in originals
        for reason in image.reasons
    )

    calibration = result.calibration
    assert calibration.opencv_rms < 1.0
    assert 300 < calibration.camera_matrix[0][0] < 1000
    assert 300 < calibration.camera_matrix[1][1] < 1000
    assert 0 < calibration.camera_matrix[0][2] < calibration.image_size[0]
    assert 0 < calibration.camera_matrix[1][2] < calibration.image_size[1]
