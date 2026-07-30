"""
A production-quality, installable Python package that audits the quality of
checkerboard image datasets used for OpenCV monocular camera calibration.
"""

from importlib.metadata import PackageNotFoundError, version

from .config import AuditConfig
from .exceptions import (
    CalibrationAuditError,
    CalibrationFailedError,
    DatasetValidationError,
    InsufficientViewsError,
    InvalidConfigurationError,
    OutputExistsError,
)
from .models import PatternSpec

try:
    __version__ = version("opencv-calibration-audit")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "AuditConfig",
    "CalibrationAuditError",
    "CalibrationFailedError",
    "DatasetValidationError",
    "InsufficientViewsError",
    "InvalidConfigurationError",
    "OutputExistsError",
    "PatternSpec",
    "__version__",
]
