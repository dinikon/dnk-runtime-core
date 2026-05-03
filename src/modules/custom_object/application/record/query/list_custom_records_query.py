from __future__ import annotations

from dataclasses import dataclass

from src.modules.runtime_data import FilterExpression, SortSpec
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListCustomRecordsQuery:
    """Query списка runtime-записей кастомного объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    filters: tuple[FilterExpression, ...]
    sorting: tuple[SortSpec, ...]
    limit: int
    offset: int


__all__ = ["ListCustomRecordsQuery"]
