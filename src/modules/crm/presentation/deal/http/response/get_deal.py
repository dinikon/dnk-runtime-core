from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from src.modules.crm.presentation.sales.response_values import (
    OwnerBasketResponse,
    BasketSummaryResponse,
    PointsResponse,
)


class GetDealResponse(BaseModel):
    """Отдельный ответ чтения полной карточки."""

    id: UUID
    title: str
    funnel_id: UUID
    stage_id: UUID
    position_revision: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    contact_ids: tuple[UUID, ...]
    company_ids: tuple[UUID, ...]
    source_lead_id: UUID | None
    source_lead_snapshot: dict[str, str | None] | None
    lifecycle_state: str
    basket: OwnerBasketResponse
    points: PointsResponse
