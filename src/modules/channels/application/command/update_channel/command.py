from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateChannelCommand:
    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    name: str | None = None
    is_active: bool | None = None
    config_version: int | None = None
    connection_settings: dict | None = field(default=None, repr=False)
