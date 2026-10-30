from pydantic import BaseModel
from src.modules.channels.application.content_delivery.query.get_content_deliveries.dto import (
    GetContentDeliveriesResultDTO,
)
from src.modules.channels.presentation.content_delivery.http.response.fields import (
    ContentDeliveryTargetResponse,
)


class GetContentDeliveriesResponse(BaseModel):
    """Публичный результат отдельного сценария get_content_deliveries."""

    items: tuple[ContentDeliveryTargetResponse, ...]

    @classmethod
    def from_dto(
        cls, value: GetContentDeliveriesResultDTO
    ) -> "GetContentDeliveriesResponse":
        """Выбирает безопасные поля каждой цели."""
        return cls(
            items=tuple(
                ContentDeliveryTargetResponse.from_row(row) for row in value.items
            )
        )
