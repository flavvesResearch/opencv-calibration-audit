"""Domain-specific exceptions for the calibration audit library."""


class CalibrationAuditError(Exception):
    """Base exception for all errors raised by this library."""


class InvalidConfigurationError(CalibrationAuditError):
    """Raised when the provided configuration is invalid."""


class DatasetValidationError(CalibrationAuditError):
    """Raised when the input dataset fails validation."""


class UnsupportedImageError(DatasetValidationError):
    """Raised when an image decodes to an unsupported dtype or channel layout."""


class InsufficientViewsError(DatasetValidationError):
    """Raised when not enough valid views are found for calibration."""


class CalibrationFailedError(CalibrationAuditError):
    """Raised when the camera calibration process fails."""


class OutputExistsError(CalibrationAuditError):
    """Raised when the output directory exists and --overwrite is not specified."""
