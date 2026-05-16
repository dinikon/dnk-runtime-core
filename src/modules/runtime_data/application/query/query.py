from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class RuntimeSearchRecordsQuery:
    """Application query for searching runtime records by public DSL."""

    tenant_id: EntityIdVO
    object_name: str
    filter_dsl: Mapping[str, Any] | None
    sort_dsl: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    limit: int = 50
    offset: int = 0


__all__ = ["RuntimeSearchRecordsQuery"]
