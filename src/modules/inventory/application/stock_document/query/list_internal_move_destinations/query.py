from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListInternalMoveDestinationsQuery:
    """Задаёт поиск активных назначений в складе конкретного ручного документа."""

    document_id: UUID
    search: str | None = None
    offset: int = 0
    limit: int = 20
    location_id: UUID | None = None
