from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO


@dataclass(slots=True, frozen=True)
class OfferHistoryQuery:
    """Параметры чтения истории предложения."""

    tenant_id: EntityIdVO
    offer_id: OfferIdVO
    filters: dict[str, Any]
    offset: int = 0
    limit: int = 50
    sort: str = "observed_at"
    direction: str = "desc"
    pagination: str = "offset"
    cursor: str | None = None
    include_total: bool = False


__all__ = ["OfferHistoryQuery"]
