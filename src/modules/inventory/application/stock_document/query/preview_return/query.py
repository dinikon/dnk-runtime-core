from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreviewReturnLine:
    """Назначает положительное количество конкретной исходной позиции строке плана."""

    client_line_id: UUID
    document_line_id: UUID
    quantity: Decimal
    uom: str
    source_position_id: UUID | None = None
    location_id: UUID | None = None
    stock_status: str | None = None


@dataclass(frozen=True, slots=True)
class PreviewReturnQuery:
    """Передаёт самостоятельное намерение физического возврата в tenant."""

    document_id: UUID
    expected_version: int
    lines: tuple[PreviewReturnLine, ...]
