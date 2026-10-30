from dataclasses import dataclass
from src.modules.channels.application.content_delivery.contracts import (
    ContentWorkSnapshot,
)


@dataclass(frozen=True, slots=True)
class PrepareContentDeliveryResultDTO:
    """Результат конкретного сценария prepare_content_delivery."""

    snapshot: ContentWorkSnapshot | None
