from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.field.value_object.field_type import (
    FieldTypeVO,
)
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum


@dataclass(frozen=True, slots=True)
class ValidatedFieldSpec:
    """Нормализованное и валидированное описание поля runtime-объекта."""

    name: str
    type: str
    kind: FieldKind
    field_type: FieldTypeVO
    label: str
    description: str
    is_nullable: bool
    default: str | None
    options: dict[str, str]
    settings: dict[str, str]


@dataclass(frozen=True, slots=True)
class ValidatedIndexSpec:
    """Нормализованное и валидированное описание индекса runtime-таблицы."""

    name: str
    fields: tuple[str, ...]
    is_unique: bool = False
    is_generated: bool = False


@dataclass(frozen=True, slots=True)
class ValidatedRelationSpec:
    """Нормализованное и валидированное описание relation/FK."""

    name: str
    label: str | None
    relation_type: RelationTypeEnum
    source_object: str
    target_object: str
    owning_object: str | None
    fk_field: str | None
    referenced_object: str | None
    referenced_field: str | None
    source_relation_name: str
    target_relation_name: str
    relation_table_name: str | None
    source_join_column_name: str | None
    target_join_column_name: str | None
    on_delete: str
    is_required: bool
    is_unique: bool
    kind: str
    settings: dict[str, Any]
    foreign_key_name: str | None = None
    fk_index_name: str | None = None
    unique_index_name: str | None = None


@dataclass(frozen=True, slots=True)
class ValidatedObjectSpec:
    """Нормализованное и валидированное описание runtime-объекта."""

    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    kind: ObjectKind
    fields: tuple[ValidatedFieldSpec, ...]
    indexes: tuple[ValidatedIndexSpec, ...] = ()
    relations: tuple[ValidatedRelationSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidatedSchemaSpec:
    """Нормализованная и валидированная спецификация runtime-схемы."""

    version: str | None
    code: str
    label: str
    objects: tuple[ValidatedObjectSpec, ...]

    def get_object(self, object_name: str) -> ValidatedObjectSpec | None:
        """Ищет object spec по singular или plural имени."""
        normalized = object_name.strip()
        for item in self.objects:
            if item.singular_name == normalized or item.plural_name == normalized:
                return item
        return None
