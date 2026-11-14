from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
)
from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_lot import StockLotPolicy
from src.modules.inventory.domain.policy.stock_serial import StockSerialPolicy
from src.modules.inventory.domain.stock_lot.error import (
    InvalidStockLotSnapshotError,
    LotTrackingNotAllowedError,
    StockLotItemMismatchError,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
    SerialTrackingNotAllowedError,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class StockTrackingDatesPolicy:
    """Проверяет прослеживаемость и получает даты исключительно из связанной партии."""

    @staticmethod
    def resolve(
        *,
        inventory_item: InventoryItemTrackingSnapshot,
        lot_id: StockLotIdVO | None,
        lot: StockLotSnapshot | None,
        serial: StockSerialSnapshot | None,
    ) -> StockDatesVO | None:
        """Возвращает даты LOT/LOT_AND_SERIAL либо отсутствие источника для NONE/SERIAL."""
        if not isinstance(inventory_item, InventoryItemTrackingSnapshot):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Нужен снимок настроек прослеживаемости товара."
            )
        inventory_item.ensure_valid()
        if inventory_item.tracking_mode.requires_serial:
            if not isinstance(serial, StockSerialSnapshot):
                raise InvalidStockSerialSnapshotError(
                    "Нужен снимок серийного экземпляра."
                )
            serial.ensure_valid()
            StockSerialPolicy.ensure_compatible(
                inventory_item_id=serial.inventory_item_id,
                inventory_item=inventory_item,
                lot_id=serial.lot_id,
                lot=lot,
            )
            if serial.lot_id != lot_id:
                raise InvalidStockSerialSnapshotError(
                    "Партия экземпляра не соответствует измерениям операции."
                )
        elif serial is not None:
            raise SerialTrackingNotAllowedError("Режим товара не допускает экземпляры.")
        if inventory_item.tracking_mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            if (
                not isinstance(lot, StockLotSnapshot)
                or not isinstance(lot.id, StockLotIdVO)
                or not isinstance(lot.dates, StockDatesVO)
            ):
                raise InvalidStockLotSnapshotError(
                    "Нужен снимок связанной партии с датами."
                )
            StockLotPolicy.ensure_compatible(
                inventory_item_id=lot.inventory_item_id, inventory_item=inventory_item
            )
            if lot.id != lot_id:
                raise StockLotItemMismatchError(
                    "Снимок не соответствует партии операции."
                )
            return lot.dates
        if lot is not None or lot_id is not None:
            raise LotTrackingNotAllowedError("Режим товара не допускает партию.")
        return None
