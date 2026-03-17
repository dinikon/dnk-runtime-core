from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DataSourceDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID
    source_type: str
    schema: str
    url: str


@dataclass(frozen=True, slots=True)
class DeleteDataSourceResultDTO:
    data_source_id: UUID
    deleted: bool


@dataclass(frozen=True, slots=True)
class FieldMetadataDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    object_metadata_id: UUID
    field_type: str
    name: str
    label: str
    default_value: object | None
    description: str | None
    icon: str | None
    options: tuple[str, ...]
    settings: dict[str, object]
    is_active: bool
    is_nullable: bool
    is_unique: bool
    tenant_id: UUID


@dataclass(frozen=True, slots=True)
class ObjectMetadataDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID
    data_source_id: UUID
    name_singular: str
    name_plural: str
    label_singular: str
    label_plural: str
    description: str | None
    icon: str | None
    is_system: bool
    duplicate_criteria: str | None
    shortcut: str | None
    ownership_kind: str
    allows_custom_fields: bool


@dataclass(frozen=True, slots=True)
class ObjectRuntimeSchemaDTO:
    object_metadata: ObjectMetadataDTO
    fields: tuple[FieldMetadataDTO, ...]


@dataclass(frozen=True, slots=True)
class ListObjectFieldDefinitionsResultDTO:
    object_metadata_id: UUID
    fields: tuple[FieldMetadataDTO, ...]


__all__ = [
    "DataSourceDTO",
    "DeleteDataSourceResultDTO",
    "FieldMetadataDTO",
    "ListObjectFieldDefinitionsResultDTO",
    "ObjectMetadataDTO",
    "ObjectRuntimeSchemaDTO",
]
