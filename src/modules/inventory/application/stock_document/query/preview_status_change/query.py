from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreviewStatusChangeLine:
    """Назначает положительное количество конкретной исходной позиции строке плана."""

    client_line_id: UUID
    document_line_id: UUID
    source_position_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class PreviewStatusChangeQuery:
    """Передаёт самостоятельное намерение физического изменения состояния в tenant."""

    document_id: UUID
    expected_version: int
    lines: tuple[PreviewStatusChangeLine, ...]
