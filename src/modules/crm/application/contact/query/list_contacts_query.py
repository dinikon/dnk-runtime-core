from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListContactsQuery:
    """Query application-слоя на список контактов tenant с пагинацией."""

    tenant_id: EntityIdVO
    limit: int
    offset: int
    filter_dsl: Mapping[str, Any] | None = None
    sort_dsl: Sequence[Mapping[str, Any]] = ()
