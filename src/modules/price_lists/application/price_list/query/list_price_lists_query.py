from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListPriceListsQuery:
    """Параметры запроса list_price_lists."""

    tenant_id: EntityIdVO
    scope: str = "current"


__all__ = ["ListPriceListsQuery"]
