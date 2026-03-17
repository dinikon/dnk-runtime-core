from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetObjectRuntimeSchemaQuery:
    tenant_id: UUID
    name_singular: str


@dataclass(frozen=True, slots=True)
class ListObjectFieldDefinitionsQuery:
    object_metadata_id: UUID


__all__ = [
    "GetObjectRuntimeSchemaQuery",
    "ListObjectFieldDefinitionsQuery",
]
