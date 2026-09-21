from __future__ import annotations
from enum import StrEnum


class RoundingMode(StrEnum):
    """Supported explicit Decimal rounding policies."""

    HALF_UP = "ROUND_HALF_UP"
    HALF_EVEN = "ROUND_HALF_EVEN"
    DOWN = "ROUND_DOWN"
    UP = "ROUND_UP"


__all__ = ["RoundingMode"]
