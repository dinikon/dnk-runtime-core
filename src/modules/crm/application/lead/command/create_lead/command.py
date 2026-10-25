from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from src.modules.crm.application.basket.values import (
    BasketInput,
    OwnerBasketProjection,
    BasketSummaryProjection,
)
from src.modules.crm.application.contact_point.dto import (
    ContactPointDraftDTO,
    ContactPointsDTO,
)
from src.modules.crm.application.lead.port.read_row import LeadReadRowDTO


@dataclass(frozen=True, slots=True)
class CreateLeadCommand:
    """Явный вход сценария CreateLead."""

    tenant_id: UUID
    actor_id: UUID
    title: str
    basket: BasketInput
    funnel_id: UUID | None = None
    phones: tuple[ContactPointDraftDTO, ...] | None = None
    emails: tuple[ContactPointDraftDTO, ...] | None = None
    locale: str = "uk"
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    company_name: str | None = None
    contact_id: UUID | None = None
    company_id: UUID | None = None
    contact_overrides: frozenset[str] = frozenset()
