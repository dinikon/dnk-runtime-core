from dataclasses import dataclass

from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidFulfillmentShipmentLineBindingError,
)
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO


@dataclass(frozen=True, slots=True)
class FulfillmentShipmentLineBindingVO:
    """Назначает распределению явно переданный ID новой строки Shipment."""

    allocation_id: FulfillmentAllocationIdVO
    shipment_line_id: ShipmentLineIdVO

    def __post_init__(self) -> None:
        """Требует номинальные типы обоих идентификаторов без генерации значений."""
        if not isinstance(
            self.allocation_id, FulfillmentAllocationIdVO
        ) or not isinstance(self.shipment_line_id, ShipmentLineIdVO):
            raise InvalidFulfillmentShipmentLineBindingError(
                "Нужны FulfillmentAllocationIdVO и ShipmentLineIdVO."
            )
