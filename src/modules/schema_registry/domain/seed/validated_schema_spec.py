from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.field.value_object.field_type import (
    FieldTypeVO,
)
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum


@dataclass(frozen=True, slots=True)
class ValidatedFieldSpec:
    name: str
    type: str
    field_type: FieldTypeVO
    label: str
    description: str
    is_nullable: bool
    default: str | None
    options: dict[str, str]
    settings: dict[str, str]


@dataclass(frozen=True, slots=True)
class ValidatedIndexSpec:
    name: str
    fields: tuple[str, ...]
    is_unique: bool = False
    is_generated: bool = False


@dataclass(frozen=True, slots=True)
class ValidatedRelationSpec:
    name: str
    relation_type: RelationTypeEnum
    source_field: str
    target_object: str
    target_field: str
    on_delete: str
    unique_index_name: str | None = None


@dataclass(frozen=True, slots=True)
class ValidatedObjectSpec:
    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    fields: tuple[ValidatedFieldSpec, ...]
    indexes: tuple[ValidatedIndexSpec, ...] = ()
    relations: tuple[ValidatedRelationSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidatedSchemaSpec:
    version: str | None
    code: str
    label: str
    objects: tuple[ValidatedObjectSpec, ...]

    def get_object(self, object_name: str) -> ValidatedObjectSpec | None:
        normalized = object_name.strip()
        for item in self.objects:
            if item.singular_name == normalized or item.plural_name == normalized:
                return item
        return None
