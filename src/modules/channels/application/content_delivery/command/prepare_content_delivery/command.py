from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareContentDeliveryCommand:
    """Вход конкретного сценария prepare_content_delivery."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
    representation_id: UUID
    publication_id: UUID
    job_id: UUID
    lock_token: str
