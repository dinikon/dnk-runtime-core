from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareStatusChangeLineDTO:
    """Передаёт точный остаток плана и актуальные настройки выбора прослеживаемости."""

    document_line_id: UUID
    position: int
    planned_quantity: Decimal
    executed_quantity: Decimal
    inventory_item_id: UUID
    sku: str
    base_uom: str
    current_base_uom: str
    remaining_quantity: Decimal
    quantity_step: Decimal
    tracking_mode: str
    expiration_mode: str


@dataclass(frozen=True, slots=True)
class PrepareStatusChangeResultDTO:
    """Возвращает серверное основание формы изменения состояния с версией документа."""

    document_id: UUID
    version: int
    status: str
    warehouse_id: UUID
    reason: str
    target_status: str
    lines: tuple[PrepareStatusChangeLineDTO, ...]
