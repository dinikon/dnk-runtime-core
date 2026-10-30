from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RefreshPublicationStockResultDTO:
    """Идентификаторы запланированных операций refresh_publication_stock."""

    operation_ids: tuple[UUID, ...]
