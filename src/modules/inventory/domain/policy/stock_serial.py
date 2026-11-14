from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
)
from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    InvalidSerialConfigurationError,
    InvalidStockSerialValueError,
    SerialTrackingNotAllowedError,
    StockSerialItemMismatchError,
    StockSerialLotMismatchError,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class StockSerialPolicy:
    """Проверяет серийный режим, принадлежность товару и связь с партией."""

    @staticmethod
    def ensure_compatible(
        *,
        inventory_item_id: InventoryItemIdVO,
        inventory_item: InventoryItemTrackingSnapshot,
        lot_id: StockLotIdVO | None,
        lot: StockLotSnapshot | None = None,
    ) -> None:
        """Разрешает SERIAL без партии или LOT_AND_SERIAL с партией того же товара."""
        if not isinstance(inventory_item_id, InventoryItemIdVO) or (
            lot_id is not None and not isinstance(lot_id, StockLotIdVO)
        ):
            raise InvalidStockSerialValueError(
                "Нужны типизированные ID экземпляра и партии."
            )
        if (
            not isinstance(inventory_item, InventoryItemTrackingSnapshot)
            or not isinstance(inventory_item.inventory_item_id, InventoryItemIdVO)
            or not isinstance(inventory_item.tracking_mode, TrackingMode)
            or not isinstance(inventory_item.expiration_mode, ExpirationMode)
        ):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Нужен типизированный снимок прослеживаемости товара."
            )
        inventory_item.ensure_valid()
        if inventory_item_id != inventory_item.inventory_item_id:
            raise StockSerialItemMismatchError("Экземпляр принадлежит другому товару.")
        if not inventory_item.tracking_mode.requires_serial:
            raise SerialTrackingNotAllowedError(
                "Экземпляр допустим только при SERIAL или LOT_AND_SERIAL."
            )
        if inventory_item.tracking_mode is TrackingMode.SERIAL:
            if lot_id is not None or lot is not None:
                raise InvalidSerialConfigurationError(
                    "Режим SERIAL не допускает ссылку или снимок партии."
                )
            return
        if lot_id is None:
            raise InvalidSerialConfigurationError(
                "Режим LOT_AND_SERIAL требует связанную партию."
            )
        if (
            not isinstance(lot, StockLotSnapshot)
            or not isinstance(lot.id, StockLotIdVO)
            or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
            or not isinstance(lot.dates, StockDatesVO)
        ):
            raise InvalidStockLotSnapshotError(
                "Нужен типизированный снимок связанной партии."
            )
        if lot.id != lot_id or lot.inventory_item_id != inventory_item_id:
            raise StockSerialLotMismatchError(
                "Снимок должен относиться к связанной партии того же товара."
            )
