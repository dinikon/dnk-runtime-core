from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetReceiptDocumentQuery:
    """Запрашивает карточку поступления текущего tenant."""

    document_id: UUID
