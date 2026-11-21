from src.modules.inventory.domain.stock_location.error import (
    InvalidLocationHierarchyError,
    InvalidStockLocationSnapshotError,
    InvalidStockLocationValueError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class LocationPlacementPolicy:
    """Проверяет создание адреса в активном складе и принадлежность его родителя."""

    @staticmethod
    def ensure_allowed(
        *,
        location_id: StockLocationIdVO,
        warehouse: WarehouseSnapshot,
        parent: StockLocationSnapshot | None = None,
    ) -> None:
        """Разрешает корневую или дочернюю локацию без самоссылки и чужого склада."""
        if not isinstance(location_id, StockLocationIdVO):
            raise InvalidStockLocationValueError("Ожидался StockLocationIdVO.")
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError(
                "Ожидался снимок склада WarehouseSnapshot."
            )
        warehouse.ensure_valid()
        if not warehouse.is_active:
            raise WarehouseInactiveError("Создание локации требует активного склада.")
        if parent is None:
            return
        if not isinstance(parent, StockLocationSnapshot):
            raise InvalidStockLocationSnapshotError(
                "Ожидался снимок родительской локации."
            )
        parent.ensure_valid()
        if parent.warehouse_id != warehouse.id:
            raise StockLocationWarehouseMismatchError(
                "Родитель принадлежит другому складу."
            )
        if parent.id == location_id:
            raise InvalidLocationHierarchyError(
                "Локация не может быть своим родителем."
            )
