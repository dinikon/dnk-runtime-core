from __future__ import annotations

from dataclasses import dataclass

from src.modules.custom_object.application.field.command.custom_field_input import (
    CustomFieldInput,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class AddCustomFieldCommand:
    """Команда добавления custom field в кастомный объект."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    field: CustomFieldInput


__all__ = ["AddCustomFieldCommand"]
