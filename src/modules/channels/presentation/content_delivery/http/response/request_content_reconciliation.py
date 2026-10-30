from pydantic import BaseModel
from src.modules.channels.application.content_delivery.command.request_content_reconciliation.dto import (
    RequestContentReconciliationResultDTO,
)
from src.modules.channels.presentation.content_delivery.http.response.fields import (
    ContentDeliveryTargetResponse,
)


class RequestContentReconciliationResponse(BaseModel):
    """Публичный результат отдельного сценария request_content_reconciliation."""

    items: tuple[ContentDeliveryTargetResponse, ...]

    @classmethod
    def from_dto(
        cls, value: RequestContentReconciliationResultDTO
    ) -> "RequestContentReconciliationResponse":
        """Выбирает безопасные поля каждой цели."""
        return cls(
            items=tuple(
                ContentDeliveryTargetResponse.from_row(row) for row in value.items
            )
        )
