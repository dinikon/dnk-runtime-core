from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
    StockLocationInactiveError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class LocationAvailabilityPolicy:
    """Проверяет административную доступность адреса и соответствующего склада."""

    @staticmethod
    def ensure_available(
        *, location: StockLocationSnapshot, warehouse: WarehouseSnapshot
    ) -> None:
        """Требует тот же активный склад и локально активную локацию без обхода дерева."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError(
                "Ожидался снимок склада WarehouseSnapshot."
            )
        warehouse.ensure_valid()
        if not isinstance(location, StockLocationSnapshot):
            raise InvalidStockLocationSnapshotError("Ожидался снимок локации.")
        location.ensure_valid()
        if location.warehouse_id != warehouse.id:
            raise StockLocationWarehouseMismatchError(
                "Локация принадлежит другому складу."
            )
        if not warehouse.is_active:
            raise WarehouseInactiveError(
                "Неактивный склад недоступен для использования."
            )
        if not location.is_active:
            raise StockLocationInactiveError(
                "Неактивная локация недоступна для использования."
            )
