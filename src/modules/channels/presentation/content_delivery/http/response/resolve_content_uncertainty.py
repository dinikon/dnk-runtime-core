from pydantic import BaseModel

from src.modules.channels.application.content_delivery.command.resolve_content_uncertainty.dto import (
    ResolveContentUncertaintyResultDTO,
)
from src.modules.channels.presentation.content_delivery.http.response.fields import (
    ContentDeliveryTargetResponse,
)


class ResolveContentUncertaintyResponse(BaseModel):
    """Публичные результаты явно завершённой попытки без тела внешнего запроса."""

    items: tuple[ContentDeliveryTargetResponse, ...]

    @classmethod
    def from_dto(
        cls, value: ResolveContentUncertaintyResultDTO
    ) -> "ResolveContentUncertaintyResponse":
        """Выбирает безопасную проекцию каждой цели."""
        return cls(
            items=tuple(ContentDeliveryTargetResponse.from_row(v) for v in value.items)
        )
