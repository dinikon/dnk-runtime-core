from uuid import UUID
from typing import Literal
from pydantic import Field
from src.modules.crm.presentation.sales.http_values import StrictRequest


class NewContactRequest(StrictRequest):
    """Данные создаваемого контакта."""

    first_name: str = Field(max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    middle_name: str | None = Field(default=None, max_length=255)


class NewCompanyRequest(StrictRequest):
    """Данные создаваемой компании."""

    legal_name: str = Field(max_length=255)


class NewDealRequest(StrictRequest):
    """Данные создаваемой продажи."""

    title: str = Field(max_length=255)
    funnel_id: UUID | None = None
    additional_company_ids: tuple[UUID, ...] = ()


class ConversionLinkRequest(StrictRequest):
    """Явная пара; null указывает на создаваемую сторону."""

    contact_id: UUID | None
    company_id: UUID | None


class ConvertLeadRequest(StrictRequest):
    """Один явный план без новых произвольных телефонов/email."""

    mode: Literal[
        "contact",
        "company",
        "contact_company",
        "contact_deal",
        "company_deal",
        "contact_company_deal",
        "deal",
    ]
    expected_source_token: str = Field(min_length=64, max_length=64)
    expected_basket_revision: int = Field(ge=1)
    contact_points: tuple[UUID, ...] | None = None
    company_points: tuple[UUID, ...] | None = None
    deal_points: tuple[UUID, ...] | None = None
    contact: NewContactRequest | None = None
    company: NewCompanyRequest | None = None
    deal: NewDealRequest | None = None
    links: tuple[ConversionLinkRequest, ...] = Field(default=(), max_length=100)
