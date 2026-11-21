from dataclasses import dataclass

from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentExecutionBindingError,
)
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)


@dataclass(frozen=True, slots=True)
class ShipmentExecutionBindingVO:
    """Назначает целую фактическую строку одной плановой строке отгрузки."""

    execution_line_id: StockExecutionLineIdVO
    shipment_line_id: ShipmentLineIdVO

    def __post_init__(self) -> None:
        """Требует типизированные ID без отдельного пользовательского количества или резерва."""
        if not isinstance(
            self.execution_line_id, StockExecutionLineIdVO
        ) or not isinstance(self.shipment_line_id, ShipmentLineIdVO):
            raise InvalidShipmentExecutionBindingError(
                "Нужны ID фактической и плановой строки отгрузки."
            )
