"""Audit checkerboard datasets and calibrate monocular pinhole cameras."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("opencv-calibration-audit")
except PackageNotFoundError:
    __version__ = "0.2.0"

from .config import AuditConfig, AuditPolicy
from .exceptions import (
    CalibrationAuditError,
    CalibrationFailedError,
    DatasetValidationError,
    InsufficientViewsError,
    InvalidConfigurationError,
    OutputExistsError,
)
from .models import (
    AuditReason,
    AuditResult,
    CalibrationResult,
    DatasetMetrics,
    ImageAuditResult,
    ImageMetrics,
    ImageState,
    PatternSpec,
    QualityGateResult,
    ReasonCode,
    ReprojectionStats,
    Severity,
)
from .pipeline import audit_dataset

__all__ = [
    "AuditConfig",
    "AuditPolicy",
    "AuditReason",
    "AuditResult",
    "CalibrationAuditError",
    "CalibrationFailedError",
    "CalibrationResult",
    "DatasetMetrics",
    "DatasetValidationError",
    "ImageAuditResult",
    "ImageMetrics",
    "ImageState",
    "InsufficientViewsError",
    "InvalidConfigurationError",
    "OutputExistsError",
    "PatternSpec",
    "QualityGateResult",
    "ReasonCode",
    "ReprojectionStats",
    "Severity",
    "__version__",
    "audit_dataset",
]
