from dataclasses import dataclass
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)


@dataclass(frozen=True, slots=True)
class GetContentDeliveriesResultDTO:
    """Результаты целей для отображения без загрузки агрегатов."""

    items: tuple[ContentDeliveryRow, ...]
