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
class ListDealsQuery:
    """Явный вход чтения ListDeals."""

    tenant_id: UUID
    funnel_id: UUID | None = None
    stage_id: UUID | None = None
    search: str = ""
    converted: bool | None = None
    offset: int = 0
    limit: int = 20
    sort: str = "updated"
