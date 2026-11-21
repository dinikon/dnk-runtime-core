from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IssueActualLine:
    """Назначает положительное количество конкретной исходной позиции строке плана."""

    client_line_id: UUID
    document_line_id: UUID
    source_position_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class PostIssueCommand:
    """Передаёт самостоятельное намерение физического расхода в tenant."""

    document_id: UUID
    expected_version: int
    idempotency_key: str
    actor_id: UUID
    tenant_id: UUID
    lines: tuple[IssueActualLine, ...]
