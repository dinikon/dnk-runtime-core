from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetRuntimeRecordQuery:
    tenant_id: UUID
    object_name_singular: str
    record_id: UUID


@dataclass(frozen=True, slots=True)
class ListRuntimeRecordsQuery:
    tenant_id: UUID
    object_name_singular: str
    filters: dict[str, object] | None = None
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class RuntimeRecordPayload:
    tenant_id: UUID
    object_name_singular: str
    record_id: UUID
    values: dict[str, object]


__all__ = [
    "GetRuntimeRecordQuery",
    "ListRuntimeRecordsQuery",
    "RuntimeRecordPayload",
]
