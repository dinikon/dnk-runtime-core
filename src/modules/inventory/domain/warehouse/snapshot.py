from dataclasses import dataclass

from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class WarehouseSnapshot:
    """Неизменяемые идентичность, активность и ссылка на основную локацию склада."""

    id: WarehouseIdVO
    is_active: bool
    default_storage_location_id: StockLocationIdVO | None

    def ensure_valid(self) -> None:
        """Проверяет собственные типы снимка без загрузки основной локации."""
        if (
            not isinstance(self.id, WarehouseIdVO)
            or type(self.is_active) is not bool
            or (
                self.default_storage_location_id is not None
                and not isinstance(self.default_storage_location_id, StockLocationIdVO)
            )
        ):
            raise InvalidWarehouseSnapshotError("Нужен типизированный снимок склада.")
