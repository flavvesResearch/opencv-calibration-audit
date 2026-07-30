"""Configuration and policy models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import PatternSpec


class AuditPolicy(BaseModel):
    """Decision thresholds, kept separate from measured facts."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    min_valid_images: int = Field(10, gt=0)
    min_board_area: float = Field(0.03, gt=0, lt=1)
    max_board_area: float = Field(0.90, gt=0, lt=1)
    min_sharpness: float | None = Field(None, gt=0)
    max_per_view_error: float | None = Field(None, gt=0)
    near_border_ratio: float = Field(0.01, ge=0, lt=0.5)
    relative_sharpness_factor: float = Field(0.35, gt=0, lt=1)
    duplicate_center_distance: float = Field(0.03, gt=0)
    duplicate_log_area_distance: float = Field(0.08, gt=0)
    duplicate_rotation_degrees: float = Field(5.0, gt=0, le=180)
    duplicate_perspective_distance: float = Field(0.08, gt=0)
    min_coverage_ratio: float = Field(0.35, ge=0, le=1)
    min_scale_bins: int = Field(3, ge=1, le=5)
    min_rotation_range_degrees: float = Field(15.0, ge=0, le=360)

    @model_validator(mode="after")
    def validate_area_range(self) -> AuditPolicy:
        if self.min_board_area >= self.max_board_area:
            raise ValueError("min_board_area must be less than max_board_area")
        return self


class AuditConfig(BaseModel):
    """Public audit configuration."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    pattern: PatternSpec
    image_directory: Path | None = Field(
        None, description="Deprecated convenience value; prefer audit_dataset(image_directory=...)."
    )
    output: Path = Path("./calibration-audit-output")
    recursive: bool = False
    min_valid_images: int = Field(10, gt=0)
    min_board_area: float = Field(0.03, gt=0, lt=1)
    max_board_area: float = Field(0.90, gt=0, lt=1)
    min_sharpness: float | None = Field(None, gt=0)
    max_per_view_error: float | None = Field(None, gt=0)
    disable_fallback_detector: bool = False
    fail_on_warning: bool = False
    overwrite_output: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    coverage_cols: int = Field(4, ge=1, le=32)
    coverage_rows: int = Field(3, ge=1, le=32)
    max_file_size_mb: int = Field(100, ge=1, le=4096)
    near_border_ratio: float = Field(0.01, ge=0, lt=0.5)
    relative_sharpness_factor: float = Field(0.35, gt=0, lt=1)
    duplicate_center_distance: float = Field(0.03, gt=0)
    duplicate_log_area_distance: float = Field(0.08, gt=0)
    duplicate_rotation_degrees: float = Field(5.0, gt=0, le=180)
    duplicate_perspective_distance: float = Field(0.08, gt=0)
    min_coverage_ratio: float = Field(0.35, ge=0, le=1)
    min_scale_bins: int = Field(3, ge=1, le=5)
    min_rotation_range_degrees: float = Field(15.0, ge=0, le=360)

    @model_validator(mode="after")
    def validate_area_range(self) -> AuditConfig:
        if self.min_board_area >= self.max_board_area:
            raise ValueError("min_board_area must be less than max_board_area")
        return self

    @property
    def policy(self) -> AuditPolicy:
        return AuditPolicy(
            min_valid_images=self.min_valid_images,
            min_board_area=self.min_board_area,
            max_board_area=self.max_board_area,
            min_sharpness=self.min_sharpness,
            max_per_view_error=self.max_per_view_error,
            near_border_ratio=self.near_border_ratio,
            relative_sharpness_factor=self.relative_sharpness_factor,
            duplicate_center_distance=self.duplicate_center_distance,
            duplicate_log_area_distance=self.duplicate_log_area_distance,
            duplicate_rotation_degrees=self.duplicate_rotation_degrees,
            duplicate_perspective_distance=self.duplicate_perspective_distance,
            min_coverage_ratio=self.min_coverage_ratio,
            min_scale_bins=self.min_scale_bins,
            min_rotation_range_degrees=self.min_rotation_range_degrees,
        )
