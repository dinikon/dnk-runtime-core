from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExistingIssueLine:
    """Передаёт изменение исходного количества собственной строки."""

    id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class NewIssueLine:
    """Передаёт выбранный товар и количество новой плановой строки."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class UpdateIssueDocumentLinesCommand:
    """Передаёт намерение и версию сохранённого плана расхода."""

    document_id: UUID
    expected_version: int
    lines: tuple[ExistingIssueLine | NewIssueLine, ...]
