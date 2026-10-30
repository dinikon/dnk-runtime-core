from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.content_delivery.contracts import (
    ContentWorkSnapshot,
    ContentDeliveryResult,
)


@dataclass(frozen=True, slots=True)
class ApplyContentDeliveryCommand:
    """Вход конкретного сценария apply_content_delivery."""

    tenant_id: UUID
    snapshot: ContentWorkSnapshot
    lock_token: str
    result: ContentDeliveryResult
