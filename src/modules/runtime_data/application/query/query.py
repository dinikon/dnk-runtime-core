from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from src.modules.runtime_data.application.models import DEFAULT_SEARCH_LIMIT
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class RuntimeSearchRecordsQuery:
    """Application query for searching runtime records by public DSL."""

    tenant_id: EntityIdVO
    object_name: str
    filter_dsl: Mapping[str, Any] | None
    sort_dsl: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    limit: int = DEFAULT_SEARCH_LIMIT
    offset: int = 0


__all__ = ["RuntimeSearchRecordsQuery"]
