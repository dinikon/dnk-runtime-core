from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO


@dataclass(slots=True, frozen=True)
class OfferDTO:
    """Проекция текущего предложения для HTTP/query consumers."""

    id: OfferIdVO
    sku: str
    external_id: str
    title: str
    lifecycle_status: str
    price_list_id: PriceListIdVO
    price_list_title: str
    purchase_price: Decimal | None
    rrp: Decimal | None
    currency: str | None
    availability: str | None
    quantity: int | None
    observed_at: datetime | None
    recommended_retail_income: Decimal | None
    margin_percent: Decimal | None
    change_count: int
    historical_conversion: dict | None = None
    current_conversion: dict | None = None


@dataclass(slots=True, frozen=True)
class OfferStateDTO:
    """Историческое наблюдение и вычисляемые торговые показатели."""

    id: OfferStateIdVO
    offer_id: OfferIdVO
    sync_run_id: SyncRunIdVO
    observed_at: datetime
    purchase_price: Decimal
    rrp: Decimal | None
    currency: str
    availability: str
    quantity: int | None
    value_hash: str
    change_reason: str
    recommended_retail_income: Decimal | None
    margin_percent: Decimal | None
    historical_conversion: dict | None = None


@dataclass(slots=True, frozen=True)
class OfferPageDTO:
    """Результат offset или cursor pagination."""

    items: list[OfferDTO] | list[OfferStateDTO]
    total: int | None
    offset: int
    limit: int
    pagination: str
    next_cursor: str | None = None
    has_more: bool = False


__all__ = ["OfferDTO", "OfferStateDTO", "OfferPageDTO"]
