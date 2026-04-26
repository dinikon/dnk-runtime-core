from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CustomRecordDTO:
    """DTO runtime-записи кастомного объекта."""

    object_id: UUID
    row_id: UUID
    values: Mapping[str, Any]


__all__ = ["CustomRecordDTO"]
