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
class ChangeDealFunnelCommand:
    """Явный вход сценария ChangeDealFunnel."""

    tenant_id: UUID
    actor_id: UUID
    record_id: UUID
    expected_position_revision: int
    funnel_id: UUID
