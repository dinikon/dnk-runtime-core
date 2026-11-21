from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetWriteOffDocumentQuery:
    """Запрашивает карточку списания текущего tenant."""

    document_id: UUID
