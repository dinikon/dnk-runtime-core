from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetIssueDocumentQuery:
    """Запрашивает карточку расхода текущего tenant."""

    document_id: UUID
