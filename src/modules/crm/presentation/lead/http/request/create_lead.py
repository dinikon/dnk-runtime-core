from uuid import UUID
from pydantic import Field, model_validator
from src.modules.crm.presentation.sales.http_values import (
    StrictRequest,
    BasketRequest,
    PointRequest,
)


class CreateLeadRequest(StrictRequest):
    """Отдельный транспортный контракт create lead."""

    title: str = Field(min_length=1, max_length=255)
    basket: BasketRequest
    funnel_id: UUID | None = None
    phones: tuple[PointRequest, ...] | None = None
    emails: tuple[PointRequest, ...] | None = None
    locale: str = Field(default="uk", max_length=64)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    middle_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    contact_id: UUID | None = None
    company_id: UUID | None = None
