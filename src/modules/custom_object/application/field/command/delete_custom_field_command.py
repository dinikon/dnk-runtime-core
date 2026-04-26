from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class DeleteCustomFieldCommand:
    """Команда удаления custom field из кастомного объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    field_id: RuntimeFieldIdVO


__all__ = ["DeleteCustomFieldCommand"]
