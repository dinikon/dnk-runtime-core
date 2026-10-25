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
class UpdateLeadCommand:
    """Явный вход сценария UpdateLead."""

    tenant_id: UUID
    actor_id: UUID
    record_id: UUID
    fields: dict[str, object]
    basket: BasketInput | None = None
    phones: tuple[ContactPointDraftDTO, ...] | None = None
    emails: tuple[ContactPointDraftDTO, ...] | None = None
    locale: str = "uk"
