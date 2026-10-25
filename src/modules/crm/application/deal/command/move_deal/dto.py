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
class MoveDealResultDTO:
    """Подтверждённый результат сценария MoveDeal."""

    id: UUID
    funnel_id: UUID
    stage_id: UUID
    position_revision: int
    line_id_map: dict[str, UUID] = field(default_factory=dict)
