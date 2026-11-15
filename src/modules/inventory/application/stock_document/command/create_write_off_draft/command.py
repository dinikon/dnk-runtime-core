from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWriteOffDraftLine:
    """Передаёт исходное количество и единицу выбранного SKU."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class CreateWriteOffDraftCommand:
    """Передаёт намерение создания и доверенную область повторной отправки."""

    warehouse_id: UUID
    owner_id: UUID
    lines: tuple[CreateWriteOffDraftLine, ...]
    actor_id: UUID
    idempotency_key: str
    reason: str
