from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockIssueValuationSnapshotError,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockIssueValuationSnapshot:
    """Передаёт конкретный проведённый расход без цены, с положительным модулем базового количества."""

    posting_id: StockPostingIdVO
    ledger_entry_id: StockLedgerEntryIdVO
    position_id: StockPositionIdVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    issued_at: datetime

    def ensure_valid(self) -> None:
        """Требует номинальные ссылки, конечное положительное количество и сохранённое UTC-время ISSUE."""
        if (
            not isinstance(self.posting_id, StockPostingIdVO)
            or not isinstance(self.ledger_entry_id, StockLedgerEntryIdVO)
            or not isinstance(self.position_id, StockPositionIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or not isinstance(self.quantity.value, Decimal)
            or not self.quantity.value.is_finite()
            or self.quantity.value <= 0
        ):
            raise InvalidStockIssueValuationSnapshotError(
                "Нужны типизированные данные расхода с положительным базовым количеством."
            )
        get_uom(self.base_uom)
        StockPostingPolicy.normalize_time(self.issued_at)
        if self.issued_at.utcoffset() != timedelta(0):
            raise InvalidStockIssueValuationSnapshotError(
                "Готовый снимок расхода должен хранить время в UTC."
            )
