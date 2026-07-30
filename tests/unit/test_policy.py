"""Policy-layer tests for relative sharpness and duplicate selection."""

from __future__ import annotations

from calibration_audit import (
    AuditConfig,
    ImageAuditResult,
    ImageMetrics,
    PatternSpec,
)
from calibration_audit.pipeline import (
    _apply_duplicates,
    _apply_relative_sharpness,
    _finalize_states,
)


def image(path: str, sharpness: float) -> ImageAuditResult:
    return ImageAuditResult(
        relative_path=path,
        read_success=True,
        detection_success=True,
        corner_count=54,
        metrics=ImageMetrics(
            file_size=1,
            board_center=(0.5, 0.5),
            board_area_ratio=0.2,
            rotation_degrees=1,
            horizontal_perspective=0.1,
            vertical_perspective=0.1,
            board_sharpness=sharpness,
        ),
    )


def test_duplicate_policy_keeps_sharper_view() -> None:
    sharp = image("sharp.png", 100)
    blurred = image("blurred.png", 10)
    config = AuditConfig(
        pattern=PatternSpec(cols=9, rows=6, square_size=1),
        min_valid_images=1,
    )
    _apply_duplicates([blurred, sharp], config)
    _finalize_states([blurred, sharp])
    assert sharp.state.value == "ACCEPTED"
    assert blurred.state.value == "REJECTED"
    assert blurred.duplicate_of == "sharp.png"
    assert [reason.code.value for reason in blurred.reasons] == ["NEAR_DUPLICATE_POSE"]


def test_relative_sharpness_is_warning_not_rejection() -> None:
    low, normal, high = image("low.png", 10), image("normal.png", 100), image("high.png", 110)
    images = [low, normal, high]
    _apply_relative_sharpness(images, 0.35)
    _finalize_states(images)
    assert low.state.value == "WARNING"
    assert low.metrics.sharpness_decision_source == "relative_outlier"
    assert normal.state.value == "ACCEPTED"
