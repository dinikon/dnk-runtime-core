from dataclasses import dataclass

from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferTransitError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockTransferTransitVO:
    """Сохраняет транзитный склад и одну локацию без проверки чужого актуального состояния."""

    warehouse_id: WarehouseIdVO
    location_id: StockLocationIdVO

    def __post_init__(self) -> None:
        """Требует типизированные ссылки; принадлежность, активность и тип локации проверяет Policy."""
        if not isinstance(self.warehouse_id, WarehouseIdVO) or not isinstance(
            self.location_id, StockLocationIdVO
        ):
            raise InvalidStockTransferTransitError(
                "Нужны WarehouseIdVO и StockLocationIdVO для транзита."
            )
