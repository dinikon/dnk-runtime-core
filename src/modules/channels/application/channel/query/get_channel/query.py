from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetChannelQuery:
    """Задаёт параметры чтения get_channel в доверенном tenant."""

    tenant_id: UUID
    channel_id: UUID
