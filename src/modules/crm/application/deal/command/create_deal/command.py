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
from src.modules.crm.application.deal.port.read_row import DealReadRowDTO


@dataclass(frozen=True, slots=True)
class CreateDealCommand:
    """Явный вход сценария CreateDeal."""

    tenant_id: UUID
    actor_id: UUID
    title: str
    basket: BasketInput
    funnel_id: UUID | None = None
    phones: tuple[ContactPointDraftDTO, ...] = ()
    emails: tuple[ContactPointDraftDTO, ...] = ()
    locale: str = "uk"
    contact_ids: tuple[UUID, ...] = ()
    company_ids: tuple[UUID, ...] = ()
