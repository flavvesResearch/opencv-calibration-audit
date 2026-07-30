"""Synthetic end-to-end acceptance and failure tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml
from conftest import digest, write_synthetic_dataset

from calibration_audit import AuditConfig, AuditResult, PatternSpec, audit_dataset
from calibration_audit.exceptions import (
    DatasetValidationError,
    InsufficientViewsError,
    OutputExistsError,
)


def test_full_synthetic_audit_and_outputs(
    synthetic_audit: tuple[Path, AuditResult, dict[str, str]], tmp_path: Path
) -> None:
    directory, result, before = synthetic_audit
    assert result.passed
    assert result.dataset_metrics.accepted_count == 10
    assert len(result.calibration.camera_matrix) == 3
    assert all(len(row) == 3 for row in result.calibration.camera_matrix)
    assert all(image.reprojection is not None for image in result.images)

    output = tmp_path / "report"
    result.write_outputs(output)
    expected = {
        "report.html",
        "summary.json",
        "images.csv",
        "calibration.yaml",
        "accepted.txt",
        "rejected.txt",
        "assets/coverage_heatmap.png",
        "assets/reprojection_errors.png",
        "assets/thumbnails/0000.jpg",
    }
    assert expected <= {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    }
    summary = json.loads((output / "summary.json").read_text())
    calibration = yaml.safe_load((output / "calibration.yaml").read_text())
    html = (output / "report.html").read_text()
    assert summary["schema_version"] == 1
    assert summary["passed"] is True
    assert summary["input_directory"] == "."
    assert calibration["camera_matrix"]["rows"] == 3
    for section in (
        "Executive summary",
        "Pass/fail quality gates",
        "Coverage heatmap",
        "Calibration parameters",
        "Reprojection-error chart",
        "Metric limitations",
    ):
        assert section in html
    assert "https://" not in html and "http://" not in html
    assert before == {path.name: digest(path) for path in directory.glob("*.png")}


def test_output_refuses_nonempty_directory(
    synthetic_audit: tuple[Path, AuditResult, dict[str, str]], tmp_path: Path
) -> None:
    _, result, _ = synthetic_audit
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "user-file.txt"
    marker.write_text("preserve")
    with pytest.raises(OutputExistsError, match="not empty"):
        result.write_outputs(output)
    result.write_outputs(output, overwrite=True)
    assert marker.read_text() == "preserve"


def test_html_escapes_untrusted_filename(
    synthetic_audit: tuple[Path, AuditResult, dict[str, str]], tmp_path: Path
) -> None:
    _, original, _ = synthetic_audit
    result = original.model_copy(deep=True)
    result.images[0].relative_path = "<script>alert(1)</script>.png"
    output = tmp_path / "escaped"
    result.write_outputs(output)
    html = (output / "report.html").read_text()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_unreadable_file_is_reported_but_scan_continues(tmp_path: Path) -> None:
    paths = write_synthetic_dataset(tmp_path, count=3)
    (tmp_path / "broken.png").write_bytes(b"invalid")
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=3,
        min_board_area=0.01,
        duplicate_center_distance=0.001,
    )
    result = audit_dataset(tmp_path, config)
    broken = next(image for image in result.images if image.relative_path == "broken.png")
    assert broken.state.value == "UNREADABLE"
    assert broken.reasons[0].code.value == "IMAGE_UNREADABLE"
    assert all(path.exists() for path in paths)


def test_mixed_resolution_fails_with_groups(tmp_path: Path) -> None:
    paths = write_synthetic_dataset(tmp_path, count=2)
    image = cv2.imread(str(paths[1]))
    assert image is not None
    assert cv2.imwrite(str(paths[1]), cv2.resize(image, (640, 480)))
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=1,
        min_board_area=0.01,
    )
    with pytest.raises(DatasetValidationError, match=r"800x600.*640x480|640x480.*800x600"):
        audit_dataset(tmp_path, config)


def test_detection_failures_cause_actionable_insufficient_views(tmp_path: Path) -> None:
    blank = np.full((600, 800), 127, dtype=np.uint8)
    assert cv2.imwrite(str(tmp_path / "blank.png"), blank)
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=1,
    )
    with pytest.raises(InsufficientViewsError, match="Only 0 accepted"):
        audit_dataset(tmp_path, config)


@pytest.mark.parametrize(
    "thresholds",
    [
        {"min_board_area": 0.80, "max_board_area": 0.90},
        {"min_board_area": 0.01, "max_board_area": 0.10},
        {"min_board_area": 0.01, "min_sharpness": 1e12},
    ],
)
def test_rejection_thresholds_produce_insufficient_views(
    tmp_path: Path, thresholds: dict[str, float]
) -> None:
    write_synthetic_dataset(tmp_path, count=2)
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=1,
        duplicate_center_distance=0.001,
        **thresholds,
    )
    with pytest.raises(InsufficientViewsError):
        audit_dataset(tmp_path, config)


def test_configured_warning_and_reprojection_gates_fail(tmp_path: Path) -> None:
    write_synthetic_dataset(tmp_path, count=3)
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=3,
        min_board_area=0.01,
        max_per_view_error=0.000001,
        fail_on_warning=True,
        min_coverage_ratio=1.0,
        duplicate_center_distance=0.001,
    )
    result = audit_dataset(tmp_path, config)
    assert not result.passed
    assert {gate.name for gate in result.quality_gates if not gate.passed} == {
        "maximum_per_view_reprojection_error",
        "fail_on_warning",
    }
    assert any(
        reason.code.value == "HIGH_REPROJECTION_ERROR"
        for image in result.images
        for reason in image.reasons
    )


def test_real_cli_smoke_on_synthetic_dataset(
    synthetic_audit: tuple[Path, AuditResult, dict[str, str]], tmp_path: Path
) -> None:
    directory, _, _ = synthetic_audit
    output = tmp_path / "cli-output"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "calibration_audit",
            "analyze",
            str(directory),
            "--cols",
            "9",
            "--rows",
            "6",
            "--square-size",
            "30",
            "--min-board-area",
            "0.01",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Quality gates: PASSED" in completed.stdout
    assert (output / "report.html").is_file()
