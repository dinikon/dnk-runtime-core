from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListCustomRecordsQuery:
    """Query списка runtime-записей кастомного объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    filter_dsl: Mapping[str, Any] | None
    sort_dsl: Sequence[Mapping[str, Any]]
    limit: int
    offset: int


__all__ = ["ListCustomRecordsQuery"]
