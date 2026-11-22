from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListPublicationsQuery:
    """Передаёт серверный поиск, статус, локаль и границы страницы состава."""

    feed_id: UUID
    locale: str = "uk"
    search: str | None = None
    status: str | None = None
    limit: int = 25
    offset: int = 0
