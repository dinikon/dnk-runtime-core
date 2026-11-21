from src.modules.inventory.domain.value_object.stock_status import StockStatus
from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExistingStatusChangeLine:
    """Передаёт изменение исходного количества собственной строки."""

    id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class NewStatusChangeLine:
    """Передаёт выбранный товар и количество новой плановой строки."""

    inventory_item_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class UpdateStatusChangeDocumentLinesCommand:
    """Передаёт намерение и версию сохранённого плана изменения состояния."""

    document_id: UUID
    expected_version: int
    lines: tuple[ExistingStatusChangeLine | NewStatusChangeLine, ...] | None
    reason: str | None = None
    target_status: StockStatus | None = None
