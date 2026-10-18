from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateChannelPolicyCommand:
    """Передаёт намерение update_channel_policy с доверенным контекстом."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    revision: int
    name: str | None
    is_enabled: bool | None
