from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListContentUpdatesQuery:
    """Ограничивает историю текущим tenant, каналом и автором."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
