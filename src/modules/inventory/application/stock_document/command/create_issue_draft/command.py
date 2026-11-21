from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateIssueDraftLine:
    """Передаёт исходное количество и единицу выбранного SKU."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class CreateIssueDraftCommand:
    """Передаёт намерение создания и доверенную область повторной отправки."""

    warehouse_id: UUID
    owner_id: UUID
    lines: tuple[CreateIssueDraftLine, ...]
    actor_id: UUID
    idempotency_key: str
