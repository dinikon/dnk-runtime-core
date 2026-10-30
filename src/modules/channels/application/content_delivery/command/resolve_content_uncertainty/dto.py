from dataclasses import dataclass

from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)


@dataclass(frozen=True, slots=True)
class ResolveContentUncertaintyResultDTO:
    """Состояния целей после явно завершённой неопределённой попытки."""

    items: tuple[ContentDeliveryRow, ...]
