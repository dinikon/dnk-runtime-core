from datetime import datetime, date
from src.modules.currency.presentation.http.conversion.responses.converted_money_response import (
    ConvertedMoneyResponse,
)
from src.modules.price_lists.application.offer.dto.offer_conversion_dto import (
    OfferConversionDTO,
)
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class OfferConversionResponse(BaseModel):
    status: str
    business_date: date | None
    purchase_price: ConvertedMoneyResponse | None
    rrp: ConvertedMoneyResponse | None
    error_code: str | None

    @classmethod
    def from_dto(cls, value: OfferConversionDTO | None):
        if value is None:
            return None
        return cls(
            status=value.status,
            business_date=value.business_date,
            purchase_price=(
                ConvertedMoneyResponse.from_dto(value.purchase_price)
                if value.purchase_price
                else None
            ),
            rrp=ConvertedMoneyResponse.from_dto(value.rrp) if value.rrp else None,
            error_code=value.error_code,
        )


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
    historical_conversion: OfferConversionResponse | None = None
    current_conversion: OfferConversionResponse | None = None
    display_conversion: OfferConversionResponse | None = None

    @classmethod
    def from_dto(cls, value):
        return cls(
            id=value.id.uuid,
            sku=value.sku,
            external_id=value.external_id,
            title=value.title,
            lifecycle_status=value.lifecycle_status,
            price_list_id=value.price_list_id.uuid,
            price_list_title=value.price_list_title,
            purchase_price=value.purchase_price,
            rrp=value.rrp,
            currency=value.currency,
            availability=value.availability,
            quantity=value.quantity,
            observed_at=value.observed_at,
            recommended_retail_income=value.recommended_retail_income,
            margin_percent=value.margin_percent,
            change_count=value.change_count,
            historical_conversion=OfferConversionResponse.from_dto(
                value.historical_conversion
            ),
            current_conversion=OfferConversionResponse.from_dto(
                value.current_conversion
            ),
            display_conversion=OfferConversionResponse.from_dto(
                value.display_conversion
            ),
        )


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
    historical_conversion: OfferConversionResponse | None = None

    @classmethod
    def from_dto(cls, value):
        return cls(
            id=value.id.uuid,
            offer_id=value.offer_id.uuid,
            sync_run_id=value.sync_run_id.uuid,
            observed_at=value.observed_at,
            purchase_price=value.purchase_price,
            rrp=value.rrp,
            currency=value.currency,
            availability=value.availability,
            quantity=value.quantity,
            value_hash=value.value_hash,
            change_reason=value.change_reason,
            recommended_retail_income=value.recommended_retail_income,
            margin_percent=value.margin_percent,
            historical_conversion=OfferConversionResponse.from_dto(
                value.historical_conversion
            ),
        )


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
