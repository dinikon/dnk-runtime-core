from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CancelPublicationImportResultDTO:
    """Возвращает адрес и новую ревизию изменённой подготовки."""

    preparation_id: UUID
    revision: int
