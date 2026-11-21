from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStatusChangeDocumentQuery:
    """Запрашивает карточку изменения состояния текущего tenant."""

    document_id: UUID
