from uuid import UUID
from pydantic import Field, model_validator
from src.modules.crm.presentation.sales.http_values import (
    StrictRequest,
    BasketRequest,
    PointRequest,
)


class CreateDealRequest(StrictRequest):
    """Отдельный транспортный контракт create deal."""

    title: str = Field(min_length=1, max_length=255)
    basket: BasketRequest
    funnel_id: UUID | None = None
    phones: tuple[PointRequest, ...] = ()
    emails: tuple[PointRequest, ...] = ()
    locale: str = Field(default="uk", max_length=64)
    contact_ids: tuple[UUID, ...] = ()
    company_ids: tuple[UUID, ...] = ()
