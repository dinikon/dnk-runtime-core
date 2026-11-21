from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockReceiptValuationSnapshotError,
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
class StockReceiptValuationSnapshot:
    """Передаёт проверенный положительный приход конкретной записи без цены, текущих остатков и чужих агрегатов."""

    posting_id: StockPostingIdVO
    ledger_entry_id: StockLedgerEntryIdVO
    position_id: StockPositionIdVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    received_at: datetime

    def ensure_valid(self) -> None:
        """Требует номинальные ссылки, известную единицу, положительное количество и сохранённый UTC-момент прихода."""
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
            or not isinstance(self.received_at, datetime)
            or self.received_at.utcoffset() != timedelta(0)
        ):
            raise InvalidStockReceiptValuationSnapshotError(
                "Нужны типизированные данные положительного прихода и время в UTC."
            )
        get_uom(self.base_uom)
