from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpsertRuntimeRecordCommand:
    tenant_id: UUID
    object_name_singular: str
    record_id: UUID
    values: dict[str, object]


@dataclass(frozen=True, slots=True)
class FindRuntimeRecordQuery:
    tenant_id: UUID
    object_name_singular: str
    filters: dict[str, object]


__all__ = [
    "FindRuntimeRecordQuery",
    "UpsertRuntimeRecordCommand",
]
