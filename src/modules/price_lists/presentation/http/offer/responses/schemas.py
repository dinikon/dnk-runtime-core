from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class OfferResponse(BaseModel):
    """HTTP-представление OfferResponse."""

    id: UUID
    sku: str
    external_id: str
    title: str
    lifecycle_status: str
    price_list_id: UUID
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


class OfferStateResponse(BaseModel):
    """HTTP-представление OfferStateResponse."""

    id: UUID
    offer_id: UUID
    sync_run_id: UUID
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


class OfferPageResponse(BaseModel):
    """HTTP-представление OfferPageResponse."""

    items: list[OfferResponse] | list[OfferStateResponse]
    total: int | None
    offset: int
    limit: int
    pagination: str
    next_cursor: str | None = None
    has_more: bool = False


class OffsetOffersResponse(BaseModel):
    """Совместимая offset-страница."""

    items: list[OfferResponse] | list[OfferStateResponse]
    total: int
    offset: int
    limit: int


class CursorOffersResponse(BaseModel):
    """Cursor-страница без обязательного COUNT."""

    items: list[OfferResponse] | list[OfferStateResponse]
    limit: int
    next_cursor: str | None
    has_more: bool
    total: int | None = None


__all__ = [
    "OfferResponse",
    "OfferStateResponse",
    "OfferPageResponse",
    "OffsetOffersResponse",
    "CursorOffersResponse",
]
