from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.modules.runtime_data.application.models import DEFAULT_SEARCH_LIMIT


@dataclass(frozen=True, slots=True)
class ListBroadcastsQuery:
    """Query списка broadcast definitions tenant."""

    tenant_id: UUID | str
    filter_dsl: Mapping[str, Any] | None = None
    sort_dsl: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    limit: int = DEFAULT_SEARCH_LIMIT
    offset: int = 0


__all__ = ["ListBroadcastsQuery"]
