"""Deterministic synthetic checkerboard fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np
import pytest

from calibration_audit import AuditConfig, AuditResult, PatternSpec, audit_dataset


def checkerboard(cols: int = 9, rows: int = 6, square: int = 60) -> np.ndarray:
    image = np.zeros(((rows + 1) * square, (cols + 1) * square), dtype=np.uint8)
    for row in range(rows + 1):
        for col in range(cols + 1):
            image[
                row * square : (row + 1) * square,
                col * square : (col + 1) * square,
            ] = 255 if (row + col) % 2 == 0 else 0
    return image


QUADS = [
    [[100, 90], [650, 100], [640, 490], [110, 480]],
    [[40, 80], [560, 110], [570, 470], [50, 450]],
    [[220, 80], [750, 70], [730, 460], [210, 480]],
    [[100, 160], [620, 120], [680, 500], [130, 530]],
    [[150, 40], [690, 120], [610, 500], [90, 430]],
    [[60, 130], [510, 50], [650, 420], [120, 520]],
    [[250, 130], [720, 160], [650, 520], [180, 470]],
    [[120, 60], [580, 80], [570, 390], [130, 410]],
    [[180, 180], [700, 120], [740, 510], [210, 540]],
    [[70, 40], [700, 60], [670, 550], [100, 520]],
]


def write_synthetic_dataset(directory: Path, count: int = 10) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    source = checkerboard()
    height, width = source.shape
    source_quad = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    paths = []
    for index, destination in enumerate(QUADS[:count]):
        transform = cv2.getPerspectiveTransform(source_quad, np.float32(destination))
        view = cv2.warpPerspective(
            source,
            transform,
            (800, 600),
            flags=cv2.INTER_NEAREST,
            borderValue=127,
        )
        path = directory / f"view_{index:02d}.png"
        assert cv2.imwrite(str(path), view)
        paths.append(path)
    return paths


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session")
def synthetic_audit(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, AuditResult, dict[str, str]]:
    directory = tmp_path_factory.mktemp("synthetic-images")
    paths = write_synthetic_dataset(directory)
    before = {path.name: digest(path) for path in paths}
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=10,
        min_board_area=0.01,
        duplicate_center_distance=0.001,
        duplicate_log_area_distance=0.001,
        duplicate_rotation_degrees=0.1,
        duplicate_perspective_distance=0.001,
    )
    return directory, audit_dataset(directory, config), before
