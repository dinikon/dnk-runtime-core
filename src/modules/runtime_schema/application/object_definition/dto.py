from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateObjectCommandDTO:
    tenant_id: UUID
    data_source_id: UUID
    object_name_singular: str
    schema: str | None = None
    object_name_plural: str | None = None
    object_label_singular: str | None = None
    object_label_plural: str | None = None
    description: str | None = None
    icon: str | None = None
    shortcut: str | None = None
    is_remote: bool = False
    is_system: bool = False
    is_custom: bool = True
    is_active: bool = True
    is_ui_read_only: bool = False
    duplicate_criteria: dict[str, object] | None = None


@dataclass(slots=True, frozen=True)
class UpdateObjectCommandDTO:
    tenant_id: UUID
    object_id: UUID
    schema: str | None = None
    object_name_singular: str | None = None
    object_name_plural: str | None = None
    object_label_singular: str | None = None
    object_label_plural: str | None = None
    description: str | None = None
    icon: str | None = None
    shortcut: str | None = None
    is_active: bool | None = None
    is_ui_read_only: bool | None = None
    duplicate_criteria: dict[str, object] | None = None
    allow_ddl_rename: bool = False


@dataclass(slots=True, frozen=True)
class DeleteObjectCommandDTO:
    tenant_id: UUID
    object_id: UUID
    schema: str | None = None
    allow_destructive: bool = False


@dataclass(slots=True, frozen=True)
class ObjectDefinitionDTO:
    id: UUID
    tenant_id: UUID
    data_source_id: UUID
    object_name_singular: str
    object_name_plural: str
    object_label_singular: str
    object_label_plural: str
    description: str | None
    icon: str | None
    shortcut: str | None
    is_remote: bool
    is_system: bool
    is_custom: bool
    is_active: bool
    is_ui_read_only: bool
    created_at: datetime
    updated_at: datetime
