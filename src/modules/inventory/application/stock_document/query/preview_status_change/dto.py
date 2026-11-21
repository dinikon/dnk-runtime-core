from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StatusChangePreviewPositionDTO:
    """Показывает исходное и расчётное количество одной стороны, не выдавая временный ID за сохранённый."""

    id: UUID | None
    exists: bool
    role: str
    inventory_item_id: UUID
    sku: str
    location_id: UUID
    location_code: str
    stock_status: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal


@dataclass(frozen=True, slots=True)
class PreviewStatusChangeResultDTO:
    """Возвращает проверенный расчёт без записи фактов или удержания количества."""

    document_id: UUID
    version: int
    reason: str
    target_status: str
    positions: tuple[StatusChangePreviewPositionDTO, ...]
