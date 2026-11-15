from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListReceiptReferencesQuery:
    """Передаёт контекст строки и серверный поиск выбора фактического назначения."""

    document_id: UUID
    kind: Literal["locations", "lots", "serials"]
    document_line_id: UUID | None = None
    lot_id: UUID | None = None
    search: str | None = None
    offset: int = 0
    limit: int = 20
