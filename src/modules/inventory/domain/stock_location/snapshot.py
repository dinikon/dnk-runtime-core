from dataclasses import dataclass

from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockLocationSnapshot:
    """Неизменяемые идентичность, принадлежность, назначение и активность адреса."""

    id: StockLocationIdVO
    warehouse_id: WarehouseIdVO
    location_type: LocationType
    is_active: bool

    def ensure_valid(self) -> None:
        """Проверяет собственные типы снимка при его использовании в Policy."""
        if (
            not isinstance(self.id, StockLocationIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.location_type, LocationType)
            or type(self.is_active) is not bool
        ):
            raise InvalidStockLocationSnapshotError(
                "Нужен типизированный снимок локации."
            )
