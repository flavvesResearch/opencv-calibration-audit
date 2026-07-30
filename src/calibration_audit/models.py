"""Core data models for the calibration audit tool."""

from typing import Literal

from pydantic import BaseModel, Field


class PatternSpec(BaseModel):
    """
    Specification for the calibration pattern.

    Attributes:
        cols: Number of inner corners horizontally. Must be >= 2.
        rows: Number of inner corners vertically. Must be >= 2.
        square_size: The size of a square in the specified unit. Must be > 0.
        unit: The unit of measure for the square size.
    """

    cols: int = Field(..., ge=2, description="Number of inner corners horizontally.")
    rows: int = Field(..., ge=2, description="Number of inner corners vertically.")
    square_size: float = Field(..., gt=0, description="The size of a square in the specified unit.")
    unit: Literal["mm", "cm", "inch", "m"] = Field("mm", description="The unit of measure for the square size.")

    @property
    def pattern_size(self) -> tuple[int, int]:
        """Returns the pattern size as a (cols, rows) tuple."""
        return self.cols, self.rows
