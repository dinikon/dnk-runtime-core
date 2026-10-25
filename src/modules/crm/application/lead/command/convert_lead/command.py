from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConversionContactInput:
    """Поля только нового контакта, без перезаписи существующего."""

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None


@dataclass(frozen=True, slots=True)
class ConversionCompanyInput:
    """Поля только новой компании."""

    legal_name: str


@dataclass(frozen=True, slots=True)
class ConversionDealInput:
    """Поля новой продажи с единственной воронкой."""

    title: str
    funnel_id: UUID | None = None
    additional_company_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversionLinkInput:
    """Явная связь: None обозначает создаваемую сторону."""

    contact_id: UUID | None
    company_id: UUID | None


@dataclass(frozen=True, slots=True)
class ConvertLeadCommand:
    """Полный подтверждаемый план атомарной конвертации."""

    tenant_id: UUID
    actor_id: UUID
    lead_id: UUID
    mode: str
    expected_source_token: str
    expected_basket_revision: int
    idempotency_key: str
    contact_points: tuple[UUID, ...] | None
    company_points: tuple[UUID, ...] | None
    deal_points: tuple[UUID, ...] | None
    contact: ConversionContactInput | None = None
    company: ConversionCompanyInput | None = None
    deal: ConversionDealInput | None = None
    links: tuple[ConversionLinkInput, ...] = ()
