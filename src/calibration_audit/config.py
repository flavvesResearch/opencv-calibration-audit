"""Configuration models for the calibration audit tool."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from calibration_audit.models import PatternSpec


class AuditConfig(BaseModel):
    """
    Main configuration for the dataset audit.

    This model gathers all settings from the CLI or a configuration file.
    """

    image_directory: Path = Field(..., description="Path to the directory containing calibration images.")
    pattern: PatternSpec = Field(..., description="Specification of the calibration pattern.")

    output: Path = Field(
        Path("./calibration-audit-output"),
        description="Path to the output directory for reports and results.",
    )
    recursive: bool = Field(False, description="Discover images recursively in the input directory.")
    min_valid_images: int = Field(
        10, gt=0, description="Minimum number of valid images required to proceed with calibration."
    )
    min_board_area: float = Field(
        0.03,
        gt=0,
        lt=1,
        description="Minimum board area as a fraction of total image area.",
    )
    max_board_area: float = Field(
        0.90,
        gt=0,
        lt=1,
        description="Maximum board area as a fraction of total image area.",
    )
    min_sharpness: Optional[float] = Field(
        None, gt=0, description="Optional absolute minimum sharpness threshold."
    )
    max_per_view_error: Optional[float] = Field(
        None, gt=0, description="Optional quality-gate threshold for per-view reprojection error."
    )
    disable_fallback_detector: bool = Field(
        False, description="Do not use the fallback detector if the primary one fails."
    )
    fail_on_warning: bool = Field(False, description="Treat any warning as a failure, affecting the exit code.")
    overwrite_output: bool = Field(False, description="Allow overwriting a non-empty output directory.")
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR).")
