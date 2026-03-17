from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.modules.runtime_schema.domain.value_objects import DataSourceType, FieldType


@dataclass(frozen=True, slots=True)
class CreateDataSourceCommand:
    tenant_id: UUID
    source_type: DataSourceType | str = DataSourceType.POSTGRESQL
    schema: str | None = None
    url: str = ""


@dataclass(frozen=True, slots=True)
class DeleteDataSourceCommand:
    data_source_id: UUID


@dataclass(frozen=True, slots=True)
class CreateCustomFieldCommand:
    object_metadata_id: UUID
    tenant_id: UUID
    field_type: FieldType | str
    name: str
    label: str
    default_value: object | None = None
    is_nullable: bool = True
    is_unique: bool = False


@dataclass(frozen=True, slots=True)
class DeleteCustomFieldCommand:
    field_metadata_id: UUID
    hard_delete: bool = False


__all__ = [
    "CreateCustomFieldCommand",
    "CreateDataSourceCommand",
    "DeleteCustomFieldCommand",
    "DeleteDataSourceCommand",
]
