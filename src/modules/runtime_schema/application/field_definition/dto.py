from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateFieldCommandDTO:
    tenant_id: UUID
    object_id: UUID
    field_type: str
    field_name: str
    label: str
    schema: str | None = None
    description: str | None = None
    icon: str | None = None
    is_unique: bool = False
    is_index: bool = False
    is_nullable: bool = True
    is_ui_read_only: bool = False
    is_searchable: bool = False
    options: dict[str, object] | None = None
    settings: dict[str, object] | None = None
    default_value: dict[str, object] | None = None
    relation_target_object_id: UUID | None = None
    relation_target_field_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class UpdateFieldCommandDTO:
    tenant_id: UUID
    field_id: UUID
    schema: str | None = None
    label: str | None = None
    description: str | None = None
    icon: str | None = None
    is_unique: bool | None = None
    is_index: bool | None = None
    is_nullable: bool | None = None
    is_ui_read_only: bool | None = None
    is_searchable: bool | None = None
    options: dict[str, object] | None = None
    settings: dict[str, object] | None = None
    default_value: dict[str, object] | None = None
    relation_target_object_id: UUID | None = None
    relation_target_field_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class DeleteFieldCommandDTO:
    tenant_id: UUID
    field_id: UUID
    schema: str | None = None
    allow_destructive: bool = False


@dataclass(slots=True, frozen=True)
class FieldDefinitionDTO:
    id: UUID
    tenant_id: UUID
    object_id: UUID
    field_type: str
    field_name: str
    label: str
    description: str | None
    icon: str | None
    is_unique: bool
    is_index: bool
    is_nullable: bool
    is_ui_read_only: bool
    is_searchable: bool
    created_at: datetime
    updated_at: datetime
