from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExistingInternalMoveLine:
    """Передаёт изменение исходного количества собственной строки."""

    id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class NewInternalMoveLine:
    """Передаёт выбранный товар и количество новой плановой строки."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class UpdateInternalMoveDocumentLinesCommand:
    """Передаёт намерение и версию сохранённого плана перемещения."""

    document_id: UUID
    expected_version: int
    lines: tuple[ExistingInternalMoveLine | NewInternalMoveLine, ...]
