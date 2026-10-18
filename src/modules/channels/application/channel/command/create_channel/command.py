from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateChannelCommand:
    """Передаёт намерение create_channel с доверенным контекстом."""

    tenant_id: UUID
    actor_id: UUID
    name: str
    platform_kind: str
