from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestContentDeliveryCommand:
    """Вход конкретного сценария request_content_delivery."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    group_id: UUID
    expected_revision: int
    expected_binding_revision: int
    expected_config_revision: int
    fingerprint: str
