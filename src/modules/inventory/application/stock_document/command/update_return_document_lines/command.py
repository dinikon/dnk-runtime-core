from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExistingReturnLine:
    """Передаёт изменение исходного количества собственной строки."""

    id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class NewReturnLine:
    """Передаёт выбранный товар и количество новой плановой строки."""

    origin_execution_line_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class UpdateReturnDocumentLinesCommand:
    """Передаёт намерение и версию сохранённого плана возврата."""

    document_id: UUID
    expected_version: int
    lines: tuple[ExistingReturnLine | NewReturnLine, ...] | None
    reason: str | None = None
