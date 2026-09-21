from __future__ import annotations
from enum import StrEnum


class ConversionPurpose(StrEnum):
    """Choose whether to preserve, book or display a calculation."""

    CALCULATION = "calculation"
    BOOKING = "booking"
    DISPLAY = "display"


__all__ = ["ConversionPurpose"]
