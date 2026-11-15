from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetInternalMoveDocumentQuery:
    """Запрашивает карточку перемещения текущего tenant."""

    document_id: UUID
