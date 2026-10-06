from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeleteChannelCommand:
    """Передаёт параметры на удаление канала в доверенном tenant-контексте."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
