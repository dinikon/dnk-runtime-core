from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListPublicationsQuery:
    """Передаёт параметры чтения list_publications в текущем tenant."""

    channel_id: UUID
    offset: int = 0
    limit: int = 25
