from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExistingWriteOffLine:
    """Передаёт изменение исходного количества собственной строки."""

    id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class NewWriteOffLine:
    """Передаёт выбранный товар и количество новой плановой строки."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class UpdateWriteOffDocumentLinesCommand:
    """Передаёт намерение и версию сохранённого плана списания."""

    document_id: UUID
    expected_version: int
    lines: tuple[ExistingWriteOffLine | NewWriteOffLine, ...] | None
    reason: str | None = None
