from dataclasses import dataclass
from datetime import datetime
from typing import Any
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO


@dataclass(slots=True, frozen=True)
class ResumePriceListCommand:
    """Входные данные действия resume_price_list."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    price_list_id: PriceListIdVO


__all__ = ["ResumePriceListCommand"]
