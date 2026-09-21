from __future__ import annotations
from enum import StrEnum


class RateDatePolicy(StrEnum):
    """Rules for using the requested date or an earlier available rate."""

    EXACT = "exact"
    PREVIOUS_AVAILABLE = "previous_available"


__all__ = ["RateDatePolicy"]
