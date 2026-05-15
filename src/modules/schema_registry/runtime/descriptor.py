from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RuntimeFieldDescriptor:
    """Runtime-описание поля, нужное для gateway и type policy."""

    name: str
    type_code: str
    is_nullable: bool
    default_value: str | None
    options: Mapping[str, str]
    settings: Mapping[str, str]
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class RuntimeRelationDescriptor:
    """Runtime-описание relation между объектами для schema/API descriptor."""

    id: str
    name: str
    label: str | None
    relation_type: str
    source_object: str
    target_object: str
    source_relation_name: str
    target_relation_name: str
    owning_object: str | None
    fk_field: str | None
    referenced_object: str | None
    referenced_field: str | None
    relation_table_name: str | None
    source_join_column_name: str | None
    target_join_column_name: str | None
    on_delete: str
    is_required: bool
    is_collection: bool
    is_virtual: bool
    is_unique: bool
    kind: str
    settings: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeObjectDescriptor:
    """Runtime-описание объекта: физическая таблица, поля и relation metadata."""

    schema_name: str
    object_name: str
    table_name: str
    pk: str
    title_field: str
    fields: tuple[RuntimeFieldDescriptor, ...]
    relations: tuple[RuntimeRelationDescriptor, ...]
    kind: str = "standard"

    def field_by_name(self, field_name: str) -> RuntimeFieldDescriptor | None:
        """Ищет поле descriptor по имени после trim входного значения."""
        normalized = field_name.strip()
        for field in self.fields:
            if field.name == normalized:
                return field
        return None

    @property
    def fields_by_name(self) -> Mapping[str, RuntimeFieldDescriptor]:
        """Возвращает read-only mapping полей descriptor по имени."""
        mapping = {field.name: field for field in self.fields}
        return MappingProxyType(mapping)
