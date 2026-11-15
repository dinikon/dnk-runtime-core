from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExistingReceiptLine:
    """Передаёт изменение исходного количества собственной строки."""

    id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class NewReceiptLine:
    """Передаёт выбранный товар и количество новой плановой строки."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class UpdateReceiptDocumentLinesCommand:
    """Передаёт намерение и версию сохранённого плана поступления."""

    document_id: UUID
    expected_version: int
    lines: tuple[ExistingReceiptLine | NewReceiptLine, ...]
