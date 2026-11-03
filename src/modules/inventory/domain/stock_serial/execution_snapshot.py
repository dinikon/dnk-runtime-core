from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


@dataclass(frozen=True, slots=True)
class StockSerialExecutionSnapshot:
    """Передаёт идентичность экземпляра и единственный собственный источник дат для исполнения."""

    id: StockSerialIdVO
    inventory_item_id: InventoryItemIdVO
    lot_id: StockLotIdVO | None
    dates: StockDatesVO | None

    def ensure_valid(self) -> None:
        """Требует собственные даты самостоятельной серии либо ссылку на партию без копии дат."""
        StockSerialSnapshot(self.id, self.inventory_item_id, self.lot_id).ensure_valid()
        if (self.lot_id is None and not isinstance(self.dates, StockDatesVO)) or (
            self.lot_id is not None and self.dates is not None
        ):
            raise InvalidStockSerialSnapshotError(
                "Нужны собственные StockDatesVO либо партия без копии дат."
            )

    def identity_snapshot(self) -> StockSerialSnapshot:
        """Предоставляет существующий минимальный контракт идентичности для проверки измерений."""
        self.ensure_valid()
        return StockSerialSnapshot(self.id, self.inventory_item_id, self.lot_id)
