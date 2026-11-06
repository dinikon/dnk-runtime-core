from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentShipmentAssignmentError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO


@dataclass(frozen=True, slots=True)
class FulfillmentShipmentAssignmentRefVO:
    """Назначает распределение строке черновика Shipment независимо от фактического прогресса."""

    shipment_id: ShipmentIdVO
    shipment_line_id: ShipmentLineIdVO
    shipment_version: int
    source_plan_version: int
    assigned_at: datetime

    def __post_init__(self) -> None:
        """Нормализует явное время и проверяет номинальные ссылки и строгие версии."""
        object.__setattr__(
            self, "assigned_at", normalize_fulfillment_time(self.assigned_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует типизированные ID, целые неотрицательные версии без bool и время UTC."""
        if (
            not isinstance(self.shipment_id, ShipmentIdVO)
            or not isinstance(self.shipment_line_id, ShipmentLineIdVO)
            or type(self.shipment_version) is not int
            or self.shipment_version < 0
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
        ):
            raise InvalidFulfillmentShipmentAssignmentError(
                "Нужны ссылки Shipment и строгие неотрицательные версии без bool."
            )
        normalize_fulfillment_time(self.assigned_at)
        if self.assigned_at.utcoffset() != timedelta(0):
            raise InvalidFulfillmentShipmentAssignmentError(
                "Момент назначения должен храниться в UTC."
            )
