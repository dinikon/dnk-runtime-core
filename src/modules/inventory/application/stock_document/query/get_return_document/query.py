from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetReturnDocumentQuery:
    """Запрашивает карточку возврата текущего tenant."""

    document_id: UUID
