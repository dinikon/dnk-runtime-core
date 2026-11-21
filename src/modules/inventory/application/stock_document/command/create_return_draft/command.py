from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateReturnDraftLine:
    """Передаёт исходное количество и единицу выбранного SKU."""

    origin_execution_line_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class CreateReturnDraftCommand:
    """Передаёт намерение создания и доверенную область повторной отправки."""

    origin_execution_id: UUID
    lines: tuple[CreateReturnDraftLine, ...]
    actor_id: UUID
    idempotency_key: str
    reason: str
