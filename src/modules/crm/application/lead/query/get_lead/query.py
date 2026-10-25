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
class GetLeadQuery:
    """Явный вход чтения GetLead."""

    tenant_id: UUID
    record_id: UUID
