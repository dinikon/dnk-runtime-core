from uuid import UUID
from pydantic import Field
from src.modules.crm.presentation.sales.http_values import StrictRequest


class MoveLeadRequest(StrictRequest):
    """Явный транспорт перемещения карточки."""

    expected_position_revision: int = Field(ge=1)
    stage_id: UUID
