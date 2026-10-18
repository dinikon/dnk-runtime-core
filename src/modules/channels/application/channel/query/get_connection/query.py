from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetConnectionQuery:
    """Задаёт параметры чтения get_connection в доверенном tenant."""

    tenant_id: UUID
    channel_id: UUID
