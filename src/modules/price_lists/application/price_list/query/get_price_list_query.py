from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO


@dataclass(slots=True, frozen=True)
class GetPriceListQuery:
    """Параметры запроса get_price_list."""

    tenant_id: EntityIdVO
    price_list_id: PriceListIdVO


__all__ = ["GetPriceListQuery"]
