from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListInternalMoveSourcesQuery:
    """Ограничивает поиск источников конкретной строкой внутреннего перемещения документа."""

    document_id: UUID
    document_line_id: UUID
    search: str | None = None
    offset: int = 0
    limit: int = 20
    position_id: UUID | None = None
