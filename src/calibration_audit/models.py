"""Typed, serializable public data models."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class PatternSpec(BaseModel):
    """Checkerboard specification; rows and columns are inner-corner counts."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    cols: int = Field(..., ge=2)
    rows: int = Field(..., ge=2)
    square_size: float = Field(..., gt=0)
    unit: Literal["mm", "cm", "inch", "m"] = "mm"

    @property
    def pattern_size(self) -> tuple[int, int]:
        return self.cols, self.rows

    @property
    def square_size_metres(self) -> float:
        factors = {"mm": 0.001, "cm": 0.01, "inch": 0.0254, "m": 1.0}
        return self.square_size * factors[self.unit]


class ImageState(str, Enum):
    ACCEPTED = "ACCEPTED"
    WARNING = "WARNING"
    REJECTED = "REJECTED"
    UNREADABLE = "UNREADABLE"


class Severity(str, Enum):
    WARNING = "WARNING"
    ERROR = "ERROR"


class ReasonCode(str, Enum):
    IMAGE_UNREADABLE = "IMAGE_UNREADABLE"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    RESOLUTION_MISMATCH = "RESOLUTION_MISMATCH"
    PATTERN_NOT_FOUND = "PATTERN_NOT_FOUND"
    PARTIAL_PATTERN = "PARTIAL_PATTERN"
    BOARD_TOO_SMALL = "BOARD_TOO_SMALL"
    BOARD_TOO_LARGE = "BOARD_TOO_LARGE"
    BOARD_CLIPPED_OR_NEAR_BORDER = "BOARD_CLIPPED_OR_NEAR_BORDER"
    LOW_SHARPNESS = "LOW_SHARPNESS"
    EXPOSURE_TOO_DARK = "EXPOSURE_TOO_DARK"
    EXPOSURE_TOO_BRIGHT = "EXPOSURE_TOO_BRIGHT"
    NEAR_DUPLICATE_POSE = "NEAR_DUPLICATE_POSE"
    HIGH_REPROJECTION_ERROR = "HIGH_REPROJECTION_ERROR"
    INSUFFICIENT_VALID_IMAGES = "INSUFFICIENT_VALID_IMAGES"
    LOW_FIELD_COVERAGE = "LOW_FIELD_COVERAGE"
    LOW_SCALE_DIVERSITY = "LOW_SCALE_DIVERSITY"
    LOW_POSE_DIVERSITY = "LOW_POSE_DIVERSITY"


class AuditReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ReasonCode
    severity: Severity
    message: str
    measured_value: float | str | None = None
    threshold: float | str | None = None


class ImageMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int | None = None
    height: int | None = None
    channels: int | None = None
    file_size: int
    global_sharpness: float | None = None
    board_sharpness: float | None = None
    sharpness_decision_source: Literal[
        "user_threshold", "relative_outlier", "none"
    ] = "none"
    mean_intensity: float | None = None
    near_black_ratio: float | None = None
    near_white_ratio: float | None = None
    board_center: tuple[float, float] | None = None
    board_area_ratio: float | None = None
    rotation_degrees: float | None = None
    horizontal_perspective: float | None = None
    vertical_perspective: float | None = None
    border_distance_ratio: float | None = None


class ReprojectionStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rmse_px: float
    mean_px: float
    median_px: float
    max_px: float
    point_count: int


class ImageAuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    read_success: bool = False
    detection_success: bool = False
    detection_method: str | None = None
    detection_duration_ms: float | None = None
    corner_count: int = 0
    corners: list[list[float]] = Field(default_factory=list)
    metrics: ImageMetrics
    state: ImageState = ImageState.REJECTED
    reasons: list[AuditReason] = Field(default_factory=list)
    duplicate_of: str | None = None
    reprojection: ReprojectionStats | None = None


class DatasetMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discovered_count: int
    readable_count: int
    detected_count: int
    accepted_count: int
    warning_count: int
    rejected_count: int
    unreadable_count: int
    detection_rate: float
    coverage_grid: list[list[int]]
    occupied_coverage_cells: int
    coverage_ratio: float
    corner_density_grid: list[list[int]]
    scale_min: float | None = None
    scale_max: float | None = None
    scale_median: float | None = None
    scale_iqr: float | None = None
    occupied_scale_bins: int = 0
    rotation_range_degrees: float | None = None
    horizontal_perspective_range: float | None = None
    vertical_perspective_range: float | None = None
    duplicate_count: int = 0


class CalibrationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_model: Literal["pinhole"] = "pinhole"
    image_size: tuple[int, int]
    opencv_rms: float
    camera_matrix: list[list[float]]
    distortion_coefficients: list[float]
    rotation_vectors: list[list[float]]
    translation_vectors: list[list[float]]
    calibration_flags: int
    mean_per_view_rmse_px: float


class QualityGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    message: str
    measured_value: float | int | None = None
    threshold: float | int | None = None


class AuditResult(BaseModel):
    """Complete audit result. ``write_outputs`` never mutates source images."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    tool_version: str
    generated_at: str
    input_directory: str
    configuration: dict[str, Any]
    pattern: PatternSpec
    dataset_metrics: DatasetMetrics
    quality_gates: list[QualityGateResult]
    calibration: CalibrationResult
    images: list[ImageAuditResult]
    warnings: list[AuditReason] = Field(default_factory=list)
    errors: list[AuditReason] = Field(default_factory=list)
    _source_directory: Path | None = PrivateAttr(default=None)

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in self.quality_gates)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "discovered_images": self.dataset_metrics.discovered_count,
            "accepted_images": self.dataset_metrics.accepted_count,
            "opencv_rms": self.calibration.opencv_rms,
            "mean_per_view_rmse_px": self.calibration.mean_per_view_rmse_px,
        }

    def write_outputs(self, output_directory: Path, *, overwrite: bool = False) -> None:
        from .reporting import write_outputs

        write_outputs(self, output_directory, overwrite=overwrite)

    @property
    def source_directory(self) -> Path:
        """Runtime-only source root, excluded from serialized reports."""

        return self._source_directory or Path(self.input_directory)

    def _bind_source_directory(self, directory: Path) -> None:
        self._source_directory = directory.resolve()
