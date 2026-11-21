from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateReceiptDraftLine:
    """Передаёт исходное количество и единицу выбранного SKU."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class CreateReceiptDraftCommand:
    """Передаёт намерение создания и доверенную область повторной отправки."""

    warehouse_id: UUID
    owner_id: UUID
    lines: tuple[CreateReceiptDraftLine, ...]
    actor_id: UUID
    idempotency_key: str
