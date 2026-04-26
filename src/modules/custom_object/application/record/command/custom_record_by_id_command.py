from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CustomRecordByIdCommand:
    """Команда операции над runtime-записью кастомного объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    row_id: Any


__all__ = ["CustomRecordByIdCommand"]
