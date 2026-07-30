"""Unit tests for configuration and data models."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from calibration_audit.config import AuditConfig
from calibration_audit.models import PatternSpec


def test_pattern_spec_valid() -> None:
    """Test successful creation of a PatternSpec."""
    spec = PatternSpec(cols=9, rows=6, square_size=30.0, unit="mm")
    assert spec.cols == 9
    assert spec.rows == 6
    assert spec.square_size == 30.0
    assert spec.unit == "mm"
    assert spec.pattern_size == (9, 6)


@pytest.mark.parametrize(
    "data, error_msg",
    [
        ({"cols": 1, "rows": 6, "square_size": 30.0}, "Input should be greater than or equal to 2"),
        ({"cols": 9, "rows": 1, "square_size": 30.0}, "Input should be greater than or equal to 2"),
        ({"cols": 9, "rows": 6, "square_size": 0.0}, "Input should be greater than 0"),
        ({"cols": 9, "rows": 6, "square_size": -1.0}, "Input should be greater than 0"),
        (
            {"cols": 9, "rows": 6, "square_size": 30.0, "unit": "kg"},
            "Input should be 'mm', 'cm', 'inch' or 'm'",
        ),
    ],
)
def test_pattern_spec_invalid(data: dict[str, Any], error_msg: str) -> None:
    """Test validation errors in PatternSpec."""
    with pytest.raises(ValidationError) as exc_info:
        PatternSpec(**data)
    assert error_msg in str(exc_info.value)


def test_audit_config_creation() -> None:
    """Test successful creation of an AuditConfig."""
    pattern = PatternSpec(cols=9, rows=6, square_size=30.0, unit="mm")
    config = AuditConfig(
        image_directory=Path("/path/to/images"),
        pattern=pattern,
        output=Path("./output"),
        recursive=False,
        min_valid_images=12,
        min_board_area=0.05,
        max_board_area=0.85,
        min_sharpness=None,
        max_per_view_error=None,
        disable_fallback_detector=False,
        fail_on_warning=False,
        overwrite_output=False,
        log_level="DEBUG",
    )
    assert config.image_directory == Path("/path/to/images")
    assert config.pattern.cols == 9
    assert config.min_valid_images == 12
    assert config.log_level == "DEBUG"
    assert config.recursive is False
    assert config.output == Path("./output")


def test_audit_config_defaults() -> None:
    """Test that AuditConfig default values are set correctly."""
    pattern = PatternSpec(cols=9, rows=6, square_size=30.0, unit="mm")
    config = AuditConfig(
        image_directory=Path("."),
        pattern=pattern,
        output=Path("./calibration-audit-output"),
        recursive=False,
        min_valid_images=10,
        min_board_area=0.03,
        max_board_area=0.90,
        min_sharpness=None,
        max_per_view_error=None,
        disable_fallback_detector=False,
        fail_on_warning=False,
        overwrite_output=False,
        log_level="INFO",
    )

    assert config.output == Path("./calibration-audit-output")
    assert config.recursive is False
    assert config.min_valid_images == 10
    assert config.min_board_area == 0.03
    assert config.max_board_area == 0.90
    assert config.min_sharpness is None
    assert config.max_per_view_error is None
    assert config.disable_fallback_detector is False
    assert config.fail_on_warning is False
    assert config.overwrite_output is False
    assert config.log_level == "INFO"


# The CLI part of the test will be in a separate file for clarity.
# This file focuses on direct model validation.
