from dataclasses import dataclass
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)


@dataclass(frozen=True, slots=True)
class RequestContentReconciliationResultDTO:
    """Результат конкретного сценария request_content_reconciliation."""

    items: tuple[ContentDeliveryRow, ...]
