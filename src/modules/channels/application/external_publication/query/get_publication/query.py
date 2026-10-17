from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationQuery:
    """Передаёт параметры чтения get_publication в текущем tenant."""

    channel_id: UUID
    publication_id: UUID
