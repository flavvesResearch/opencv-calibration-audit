"""Configuration, enum, and unit-conversion tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from calibration_audit import AuditConfig, PatternSpec


@pytest.mark.parametrize(
    ("unit", "value", "metres"),
    [("mm", 30.0, 0.03), ("cm", 3.0, 0.03), ("inch", 1.0, 0.0254), ("m", 0.5, 0.5)],
)
def test_unit_conversion(unit: str, value: float, metres: float) -> None:
    pattern = PatternSpec(cols=9, rows=6, square_size=value, unit=unit)  # type: ignore[arg-type]
    assert pattern.pattern_size == (9, 6)
    assert pattern.square_size_metres == pytest.approx(metres)


@pytest.mark.parametrize(
    "data",
    [
        {"cols": 1, "rows": 6, "square_size": 1},
        {"cols": 9, "rows": 1, "square_size": 1},
        {"cols": 9, "rows": 6, "square_size": 0},
        {"cols": 9, "rows": 6, "square_size": float("nan")},
        {"cols": 9, "rows": 6, "square_size": float("inf")},
        {"cols": 9, "rows": 6, "square_size": 1, "unit": "pixels"},
        {"cols": 9, "rows": 6, "square_size": 1, "unknown": True},
    ],
)
def test_invalid_pattern(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PatternSpec.model_validate(data)


def test_config_defaults_and_policy_copy() -> None:
    config = AuditConfig(pattern=PatternSpec(cols=9, rows=6, square_size=20))
    assert config.output.name == "calibration-audit-output"
    assert config.policy.min_valid_images == 10
    assert config.policy.duplicate_center_distance == 0.03


@pytest.mark.parametrize(
    "values",
    [
        {"min_board_area": 0.5, "max_board_area": 0.5},
        {"min_board_area": 0.8, "max_board_area": 0.2},
        {"min_valid_images": 0},
        {"coverage_cols": 0},
        {"max_file_size_mb": 0},
        {"log_level": "VERBOSE"},
    ],
)
def test_invalid_config(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AuditConfig(
            pattern=PatternSpec(cols=9, rows=6, square_size=20),
            **values,  # type: ignore[arg-type]
        )
