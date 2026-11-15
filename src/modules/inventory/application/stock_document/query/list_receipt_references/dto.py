from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReceiptReferenceItemDTO:
    """Передаёт данные одного варианта приёмки; даты всегда принадлежат партии."""

    id: UUID
    label: str
    lot_id: UUID | None = None
    lot_number: str | None = None
    manufactured_on: date | None = None
    expires_on: date | None = None


@dataclass(frozen=True, slots=True)
class ListReceiptReferencesResultDTO:
    """Возвращает страницу серверного выбора внутри документа и SKU строки."""

    items: tuple[ReceiptReferenceItemDTO, ...]
    total: int
    offset: int
    limit: int
