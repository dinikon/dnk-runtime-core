from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateChannelCommand:
    tenant_id: UUID
    actor_id: UUID
    name: str
    kind: str
    config_version: int
    connection_settings: dict = field(repr=False)
    is_active: bool = True
