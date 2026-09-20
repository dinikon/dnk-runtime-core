from dataclasses import dataclass
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO


@dataclass(slots=True, frozen=True)
class PreviewPriceListQuery:
    """Параметры запроса preview_price_list."""

    tenant_id: EntityIdVO
    price_list_id: PriceListIdVO
    candidate: dict[str, Any]
    limit: int = 20


__all__ = ["PreviewPriceListQuery"]
