from dataclasses import dataclass
from datetime import date
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListOffersQuery:
    """Tenant-scoped параметры чтения предложений."""

    tenant_id: EntityIdVO
    filters: dict[str, Any]
    offset: int = 0
    limit: int = 50
    sort: str = "observed_at"
    direction: str = "desc"
    include_archived: bool = False
    pagination: str = "offset"
    cursor: str | None = None
    include_total: bool = False
    business_date: date | None = None


__all__ = ["ListOffersQuery"]
