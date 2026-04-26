from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateCustomRecordCommand:
    """Команда обновления runtime-записи кастомного объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    row_id: Any
    values: Mapping[str, Any]


__all__ = ["UpdateCustomRecordCommand"]
