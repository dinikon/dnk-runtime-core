from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListReturnExecutionsQuery:
    """Передаёт документ и проверенную страницу истории."""

    document_id: UUID
    offset: int = 0
    limit: int = 20
