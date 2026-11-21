from src.modules.inventory.domain.inventory_count.error import (
    InvalidCountScopeError,
    InventoryCountContextMismatchError,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
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
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class InventoryCountConfirmationPolicy:
    """Проверяет склад и ровно выбранные адреса без чтения позиций, доступности или дерева локаций."""

    @staticmethod
    def ensure_warehouse(
        *, warehouse_id: WarehouseIdVO, warehouse: WarehouseSnapshot
    ) -> None:
        """Требует актуальный снимок того же активного склада без обязательной основной локации."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада инвентаризации.")
        warehouse.ensure_valid()
        if not isinstance(warehouse_id, WarehouseIdVO):
            raise InventoryCountContextMismatchError("Нужен ID склада инвентаризации.")
        if warehouse.id != warehouse_id:
            raise InventoryCountContextMismatchError("Передан снимок другого склада.")
        if not warehouse.is_active:
            raise WarehouseInactiveError("Инвентаризация требует активный склад.")

    @staticmethod
    def ensure_confirmable(
        *,
        warehouse_id: WarehouseIdVO,
        scope: CountScopeVO,
        warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
    ) -> None:
        """Повторно проверяет склад и точное соответствие активных локаций зафиксированной области."""
        InventoryCountConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse_id, warehouse=warehouse
        )
        if not isinstance(scope, CountScopeVO):
            raise InvalidCountScopeError("Нужна типизированная область проверки.")
        scope.ensure_valid()
        if not isinstance(locations, tuple):
            raise InventoryCountContextMismatchError("Нужен tuple снимков локаций.")
        identifiers = set()
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockLocationSnapshotError("Нужны снимки локаций.")
            location.ensure_valid()
            if location.id in identifiers:
                raise InventoryCountContextMismatchError("Снимок локации повторяется.")
            identifiers.add(location.id)
            if location.warehouse_id != warehouse_id:
                raise StockLocationWarehouseMismatchError(
                    "Адрес относится к другому складу."
                )
            if not location.is_active:
                raise StockLocationInactiveError("Выбранный адрес должен быть активен.")
        if identifiers != set(scope.location_ids):
            raise InventoryCountContextMismatchError(
                "Нужны ровно выбранные адреса; для FULL снимки локаций не передаются."
            )
