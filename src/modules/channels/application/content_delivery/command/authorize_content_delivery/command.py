from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.content_delivery.contracts import (
    ContentWorkSnapshot,
)


@dataclass(frozen=True, slots=True)
class AuthorizeContentDeliveryCommand:
    """Вход конкретного сценария authorize_content_delivery."""

    tenant_id: UUID
    snapshot: ContentWorkSnapshot
    lock_token: str
