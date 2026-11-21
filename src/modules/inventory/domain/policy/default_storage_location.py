from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
    StockLocationInactiveError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.warehouse.error import (
    DefaultStorageLocationInUseError,
    InvalidDefaultStorageLocationError,
    InvalidWarehouseSnapshotError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class DefaultStorageLocationPolicy:
    """Проверяет назначение основной STORAGE и защиту её от деактивации."""

    @staticmethod
    def ensure_assignable(
        *, location: StockLocationSnapshot, warehouse: WarehouseSnapshot
    ) -> None:
        """Разрешает назначить активную STORAGE того же склада, включая настройку заблокированного склада."""
        DefaultStorageLocationPolicy._ensure_same_warehouse(
            location=location, warehouse=warehouse
        )
        if location.location_type is not LocationType.STORAGE:
            raise InvalidDefaultStorageLocationError(
                "Основная локация должна иметь тип STORAGE."
            )
        if not location.is_active:
            raise StockLocationInactiveError("Основная локация должна быть активной.")

    @staticmethod
    def ensure_can_deactivate(
        *, location: StockLocationSnapshot, warehouse: WarehouseSnapshot
    ) -> None:
        """Требует предварительно переназначить основную локацию без проверки активности склада."""
        DefaultStorageLocationPolicy._ensure_same_warehouse(
            location=location, warehouse=warehouse
        )
        if warehouse.default_storage_location_id == location.id:
            raise DefaultStorageLocationInUseError(
                "Перед деактивацией переназначьте основную локацию склада."
            )

    @staticmethod
    def _ensure_same_warehouse(
        *, location: StockLocationSnapshot, warehouse: WarehouseSnapshot
    ) -> None:
        """Проверяет типы обоих снимков и принадлежность локации складу."""
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
