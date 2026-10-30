from typing import Protocol
from uuid import UUID
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)


class ContentDeliveryQueryRepositoryProtocol(Protocol):
    """Читает результаты целей без восстановления агрегатов ради Console."""

    async def for_representation(
        self, representation_id: UUID
    ) -> tuple[ContentDeliveryRow, ...]:
        """Возвращает безопасные проекции выбранного представления."""
        ...
