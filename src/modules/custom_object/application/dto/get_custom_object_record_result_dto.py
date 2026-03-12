from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCustomObjectRecordResultDTO:
    object_name_singular: str
    record_id: UUID
    values: dict[str, object] = field(default_factory=dict)


__all__ = ["GetCustomObjectRecordResultDTO"]
