from src.modules.inventory.domain.value_object.stock_status import StockStatus
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateStatusChangeDraftLine:
    """Передаёт исходное количество и единицу выбранного SKU."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class CreateStatusChangeDraftCommand:
    """Передаёт намерение создания и доверенную область повторной отправки."""

    warehouse_id: UUID
    owner_id: UUID
    lines: tuple[CreateStatusChangeDraftLine, ...]
    actor_id: UUID
    idempotency_key: str
    reason: str
    target_status: StockStatus
