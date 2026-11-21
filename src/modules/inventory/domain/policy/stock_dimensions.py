from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockDimensionsError,
    InvalidStockTrackingDimensionsError,
    StockDimensionsMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class StockDimensionsPolicy:
    """Проверяет неизменяемые измерения по снимкам без правил доступности операций."""

    @staticmethod
    def ensure_compatible(
        *,
        dimensions: StockDimensionsVO,
        inventory_item: InventoryItemStockSnapshot,
        location: StockLocationSnapshot,
        warehouse: WarehouseSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> None:
        """Проверяет ссылки и матрицу LOT/SERIAL, сохраняя физический учёт в неактивных адресах."""
        if not isinstance(dimensions, StockDimensionsVO):
            raise InvalidStockDimensionsError("Ожидались измерения StockDimensionsVO.")
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Ожидался учётный снимок товара."
            )
        inventory_item.ensure_valid()
        if not isinstance(location, StockLocationSnapshot):
            raise InvalidStockLocationSnapshotError("Ожидался снимок локации.")
        location.ensure_valid()
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Ожидался снимок склада.")
        warehouse.ensure_valid()
        if (
            dimensions.inventory_item_id != inventory_item.inventory_item_id
            or dimensions.location_id != location.id
            or location.warehouse_id != warehouse.id
        ):
            raise StockDimensionsMismatchError(
                "Товар, локация и склад должны соответствовать измерениям."
            )
        requires_lot = inventory_item.tracking_mode in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        )
        requires_serial = inventory_item.tracking_mode.requires_serial
        if (
            requires_lot != (dimensions.lot_id is not None)
            or requires_serial != (dimensions.serial_id is not None)
            or (not requires_lot and lot is not None)
            or (not requires_serial and serial is not None)
        ):
            raise InvalidStockTrackingDimensionsError(
                "Партия и серия должны соответствовать режиму прослеживаемости."
            )
        if requires_lot:
            if (
                not isinstance(lot, StockLotSnapshot)
                or not isinstance(lot.id, StockLotIdVO)
                or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
                or not isinstance(lot.dates, StockDatesVO)
            ):
                raise InvalidStockLotSnapshotError(
                    "Нужен типизированный снимок партии."
                )
            if (
                lot.id != dimensions.lot_id
                or lot.inventory_item_id != dimensions.inventory_item_id
            ):
                raise StockDimensionsMismatchError(
                    "Снимок партии не соответствует позиции и товару."
                )
        if requires_serial:
            if not isinstance(serial, StockSerialSnapshot):
                raise InvalidStockSerialSnapshotError(
                    "Нужен снимок серийного экземпляра."
                )
            serial.ensure_valid()
            if (
                serial.id != dimensions.serial_id
                or serial.inventory_item_id != dimensions.inventory_item_id
                or serial.lot_id != dimensions.lot_id
            ):
                raise StockDimensionsMismatchError(
                    "Серия должна относиться к тому же товару и партии позиции."
                )
