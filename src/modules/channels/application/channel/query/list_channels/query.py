from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListChannelsQuery:
    """Задаёт параметры чтения list_channels в доверенном tenant."""

    tenant_id: UUID
    offset: int = 0
    limit: int = 50
