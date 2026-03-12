from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.custom_object.domain import CustomObjectRecordEntity


@dataclass(frozen=True, slots=True)
class GetCustomObjectRecordQuery:
    tenant_id: UUID
    object_name_singular: str
    record_id: UUID


@dataclass(frozen=True, slots=True)
class CustomObjectRecord:
    record: CustomObjectRecordEntity


class CustomObjectRecordRepositoryPort(Protocol):
    async def get_by_id(
        self,
        query: GetCustomObjectRecordQuery,
    ) -> CustomObjectRecord | None: ...


@dataclass(frozen=True, slots=True)
class CreateCustomObjectDefinitionCommand:
    tenant_id: UUID
    object_name_singular: str
    object_name_plural: str | None = None
    object_label_singular: str | None = None
    object_label_plural: str | None = None
    description: str | None = None
    icon: str | None = None
    shortcut: str | None = None
    is_active: bool = True
    is_ui_read_only: bool = False


@dataclass(frozen=True, slots=True)
class CustomObjectDefinition:
    id: UUID
    object_name_singular: str
    object_name_plural: str
    object_label_singular: str
    object_label_plural: str
    description: str | None
    icon: str | None
    shortcut: str | None
    is_active: bool
    is_ui_read_only: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CreateCustomObjectFieldCommand:
    tenant_id: UUID
    object_name_singular: str
    field_type: str
    field_name: str
    label: str
    description: str | None = None
    icon: str | None = None
    is_active: bool = True
    is_unique: bool = False
    is_index: bool = False
    is_nullable: bool = True
    is_ui_read_only: bool = False
    is_searchable: bool = False
    options: dict[str, object] | None = None
    settings: dict[str, object] | None = None
    default_value: dict[str, object] | None = None
    relation_target_object_name: str | None = None
    relation_target_field_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CustomObjectFieldDefinition:
    id: UUID
    object_id: UUID
    field_type: str
    field_name: str
    label: str
    description: str | None
    icon: str | None
    is_active: bool
    is_unique: bool
    is_index: bool
    is_nullable: bool
    is_ui_read_only: bool
    is_searchable: bool
    created_at: datetime
    updated_at: datetime


class CustomObjectSchemaRepositoryPort(Protocol):
    async def create_object_definition(
        self,
        command: CreateCustomObjectDefinitionCommand,
    ) -> CustomObjectDefinition: ...

    async def create_field_definition(
        self,
        command: CreateCustomObjectFieldCommand,
    ) -> CustomObjectFieldDefinition: ...


__all__ = [
    "CreateCustomObjectDefinitionCommand",
    "CreateCustomObjectFieldCommand",
    "CustomObjectDefinition",
    "CustomObjectFieldDefinition",
    "CustomObjectRecord",
    "CustomObjectRecordRepositoryPort",
    "CustomObjectSchemaRepositoryPort",
    "GetCustomObjectRecordQuery",
]
