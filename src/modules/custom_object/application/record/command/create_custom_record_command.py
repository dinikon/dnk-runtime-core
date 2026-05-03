from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateCustomRecordCommand:
    """Команда создания runtime-записи кастомного объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    values: Mapping[str, Any]


__all__ = ["CreateCustomRecordCommand"]
