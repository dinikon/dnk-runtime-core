from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeRecordDTO:
    """Application DTO for one runtime record."""

    id: Any
    values: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeSearchRecordsResult:
    """Application DTO for a runtime record search page."""

    rows: tuple[RuntimeRecordDTO, ...]
    total: int
    limit: int
    offset: int


__all__ = ["RuntimeRecordDTO", "RuntimeSearchRecordsResult"]
