from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from src.modules.crm.presentation.sales.response_values import (
    OwnerBasketResponse,
    BasketSummaryResponse,
    PointsResponse,
)


class GetLeadResponse(BaseModel):
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
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    company_name: str | None
    contact_id: UUID | None
    company_id: UUID | None
    conversion_result: dict[str, object] | None
    basket: OwnerBasketResponse
    points: PointsResponse
