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
from src.modules.inventory.domain.stock_lot.error import (
    InvalidStockLotValueError,
    LotTrackingNotAllowedError,
    StockLotItemMismatchError,
)


class StockLotPolicy:
    """Проверяет принадлежность партии товару и допустимость партийного учёта."""

    @staticmethod
    def ensure_compatible(
        *,
        inventory_item_id: InventoryItemIdVO,
        inventory_item: InventoryItemTrackingSnapshot,
    ) -> None:
        """Разрешает партии только того же товара с LOT или LOT_AND_SERIAL."""
        if not isinstance(inventory_item_id, InventoryItemIdVO):
            raise InvalidStockLotValueError("Ожидался InventoryItemIdVO партии.")
        if (
            not isinstance(inventory_item, InventoryItemTrackingSnapshot)
            or not isinstance(inventory_item.inventory_item_id, InventoryItemIdVO)
            or not isinstance(inventory_item.tracking_mode, TrackingMode)
            or not isinstance(inventory_item.expiration_mode, ExpirationMode)
        ):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Нужен типизированный снимок прослеживаемости товара."
            )
        if inventory_item_id != inventory_item.inventory_item_id:
            raise StockLotItemMismatchError("Партия принадлежит другому товару.")
        if inventory_item.tracking_mode not in (
            TrackingMode.LOT,
            TrackingMode.LOT_AND_SERIAL,
        ):
            raise LotTrackingNotAllowedError(
                "Партия допустима только при LOT или LOT_AND_SERIAL."
            )
