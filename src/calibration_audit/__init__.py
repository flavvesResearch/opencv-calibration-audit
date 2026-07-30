"""
A production-quality, installable Python package that audits the quality of
checkerboard image datasets used for OpenCV monocular camera calibration.
"""

__version__ = "0.1.0"

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
