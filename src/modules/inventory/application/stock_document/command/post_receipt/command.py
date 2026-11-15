from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID
from src.modules.inventory.domain.value_object.stock_status import StockStatus


@dataclass(frozen=True, slots=True)
class ReceiptActualLine:
    """Передаёт стабильную строку запроса и фактическое назначение плановой строки."""

    client_line_id: UUID
    document_line_id: UUID
    quantity: Decimal
    uom: str
    location_id: UUID
    lot_id: UUID | None
    serial_id: UUID | None
    stock_status: StockStatus


@dataclass(frozen=True, slots=True)
class ReceiptCostAllocationInput:
    """Связывает введённую сумму со строкой текущего запроса."""

    client_line_id: UUID
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ReceiptCostInput:
    """Передаёт известное исходное основание; пустое распределение означает нераспределённую сумму."""

    amount: Decimal
    currency: str
    basis_kind: str
    source_system: str | None
    source_reference: str | None
    allocations: tuple[ReceiptCostAllocationInput, ...]


@dataclass(frozen=True, slots=True)
class PostReceiptCommand:
    """Описывает единственное намерение приёмки в доверенном tenant-контексте."""

    document_id: UUID
    expected_version: int
    idempotency_key: str
    actor_id: UUID
    tenant_id: UUID
    lines: tuple[ReceiptActualLine, ...]
    costs: tuple[ReceiptCostInput, ...]
