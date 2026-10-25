from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from src.modules.crm.presentation.sales.response_values import (
    OwnerBasketResponse,
    BasketSummaryResponse,
    PointsResponse,
)


class MoveLeadResponse(BaseModel):
    """Отдельный ответ подтверждённой мутации move."""

    id: UUID
    funnel_id: UUID
    stage_id: UUID
    position_revision: int
    line_id_map: dict[str, UUID]
