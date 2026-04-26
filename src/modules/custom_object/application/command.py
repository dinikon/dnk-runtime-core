from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.modules.runtime_data import FilterExpression, SortSpec
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import TenantIdVO


@dataclass(frozen=True, slots=True)
class CustomFieldInput:
    """Входные данные для создания custom field metadata и колонки."""

    field_name: str
    type: str
    label: str
    description: str = ""
    is_nullable: bool = True
    default_value: str | None = None
    options: dict[str, str] = field(default_factory=dict)
    settings: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreateCustomObjectCommand:
    """Команда создания кастомного объекта."""

    tenant_id: TenantIdVO
    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    fields: tuple[CustomFieldInput, ...] = ()


@dataclass(frozen=True, slots=True)
class CustomObjectByIdCommand:
    """Команда операции над кастомным объектом по object_id."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO


@dataclass(frozen=True, slots=True)
class AddCustomFieldCommand:
    """Команда добавления custom field в кастомный объект."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO
    field: CustomFieldInput


@dataclass(frozen=True, slots=True)
class DeleteCustomFieldCommand:
    """Команда удаления custom field из кастомного объекта."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO
    field_id: RuntimeFieldIdVO


@dataclass(frozen=True, slots=True)
class CreateCustomRecordCommand:
    """Команда создания runtime-записи кастомного объекта."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO
    values: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CustomRecordByIdCommand:
    """Команда операции над runtime-записью кастомного объекта."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO
    row_id: Any


@dataclass(frozen=True, slots=True)
class ListCustomRecordsQuery:
    """Query списка runtime-записей кастомного объекта."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO
    filters: tuple[FilterExpression, ...]
    sorting: tuple[SortSpec, ...]
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class UpdateCustomRecordCommand:
    """Команда обновления runtime-записи кастомного объекта."""

    tenant_id: TenantIdVO
    object_id: RuntimeObjectIdVO
    row_id: Any
    values: Mapping[str, Any]
