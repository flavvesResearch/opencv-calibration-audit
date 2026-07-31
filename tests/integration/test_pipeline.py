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

from calibration_audit import (
    AuditConfig,
    AuditReason,
    AuditResult,
    ImageState,
    PatternSpec,
    ReasonCode,
    Severity,
    audit_dataset,
)
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
        "report-manifest.json",
        "assets/coverage_heatmap.png",
        "assets/reprojection_errors.png",
    }
    generated = {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    }
    assert expected <= generated
    assert any(path.startswith("assets/thumbnails/") for path in generated)
    summary = json.loads((output / "summary.json").read_text())
    calibration = yaml.safe_load((output / "calibration.yaml").read_text())
    html = (output / "report.html").read_text()
    assert summary["schema_version"] == 1
    assert summary["passed"] is True
    assert summary["input_directory"] == "."
    assert summary["opencv_version"] == cv2.__version__
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
    assert html.count('class="image-preview"') == len(result.images)
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


def test_overwrite_removes_only_stale_managed_thumbnails(
    synthetic_audit: tuple[Path, AuditResult, dict[str, str]], tmp_path: Path
) -> None:
    _, original, _ = synthetic_audit
    output = tmp_path / "overwrite"
    original.write_outputs(output)
    old_thumbnails = set((output / "assets" / "thumbnails").glob("*.jpg"))
    assert len(old_thumbnails) == len(original.images)
    unrelated = output / "assets" / "thumbnails" / "user-notes.txt"
    unrelated.write_text("preserve", encoding="utf-8")

    reduced = original.model_copy(deep=True)
    reduced.images = reduced.images[:2]
    reduced.write_outputs(output, overwrite=True)

    new_thumbnails = set((output / "assets" / "thumbnails").glob("*.jpg"))
    assert len(new_thumbnails) == 2
    assert not (old_thumbnails - new_thumbnails) & set(output.rglob("*.jpg"))
    assert unrelated.read_text(encoding="utf-8") == "preserve"
    manifest = json.loads((output / "report-manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["generated_files"]) == manifest["generated_files"]
    assert {path.relative_to(output).as_posix() for path in new_thumbnails} <= set(
        manifest["generated_files"]
    )


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


def test_html_explains_decisions_and_escapes_messages(
    synthetic_audit: tuple[Path, AuditResult, dict[str, str]], tmp_path: Path
) -> None:
    _, original, _ = synthetic_audit
    result = original.model_copy(deep=True)
    image = result.images[0]
    image.state = ImageState.REJECTED
    image.reasons = [
        AuditReason(
            code=ReasonCode.LOW_SHARPNESS,
            severity=Severity.ERROR,
            message="Board <region> is below the configured threshold.",
            measured_value=12.5,
            threshold=20.0,
        )
    ]
    warning = result.images[1]
    warning.state = ImageState.WARNING
    warning.reasons = [
        AuditReason(
            code=ReasonCode.HIGH_REPROJECTION_ERROR,
            severity=Severity.WARNING,
            message="In-sample residual exceeds the configured threshold.",
            measured_value=1.25,
            threshold=1.0,
        )
    ]
    output = tmp_path / "explanations"
    result.write_outputs(output)
    html = (output / "report.html").read_text(encoding="utf-8")
    assert "LOW_SHARPNESS" in html
    assert "ERROR" in html
    assert "Board &lt;region&gt; is below the configured threshold." in html
    assert "12.5" in html
    assert "20.0" in html
    assert "Rejected before calibration" in html
    assert "Flagged after calibration" in html
    assert "in-sample" in html
    assert "not independent validation" in html
    assert 'class="rejected' in html
    assert 'class="warning' in html


def test_recursive_output_inside_input_is_rejected_before_discovery(tmp_path: Path) -> None:
    image_directory = tmp_path / "images"
    write_synthetic_dataset(image_directory, count=1)
    generated = image_directory / "audit-result"
    alias = tmp_path / "report-alias"
    generated.mkdir()
    try:
        alias.symlink_to(generated, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable on this platform")
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        recursive=True,
        output=alias,
        min_valid_images=1,
        min_board_area=0.01,
    )
    with pytest.raises(DatasetValidationError, match="output directory.*inside"):
        audit_dataset(image_directory, config)

    safe_config = config.model_copy(update={"output": tmp_path / "safe-report"})
    result = audit_dataset(image_directory, safe_config)
    with pytest.raises(DatasetValidationError, match="output directory.*inside"):
        result.write_outputs(image_directory / "different-report")


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


def test_uint16_metrics_and_unsupported_dtype_reason_are_recorded(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "images"
    destination.mkdir()
    for path in write_synthetic_dataset(source, count=3):
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert gray is not None
        assert cv2.imwrite(
            str(destination / f"{path.stem}.tiff"),
            gray.astype(np.uint16) * 257,
        )
    assert cv2.imwrite(
        str(destination / "unsupported-float.tiff"),
        np.ones((600, 800), dtype=np.float32),
    )
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=30),
        min_valid_images=3,
        min_board_area=0.01,
        duplicate_center_distance=0.001,
    )
    result = audit_dataset(destination, config)
    supported = [image for image in result.images if image.read_success]
    assert len(supported) == 3
    assert all(image.metrics.original_dtype == "uint16" for image in supported)
    assert all(image.metrics.original_bit_depth == 16 for image in supported)
    unsupported = next(
        image for image in result.images if image.relative_path == "unsupported-float.tiff"
    )
    assert unsupported.state.value == "UNREADABLE"
    assert unsupported.reasons[0].code.value == "UNSUPPORTED_IMAGE"


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
