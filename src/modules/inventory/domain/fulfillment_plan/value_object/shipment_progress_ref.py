from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentShipmentProgressRefError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO


@dataclass(frozen=True, slots=True)
class FulfillmentShipmentProgressRefVO:
    """Сохраняет привязку к строке Shipment и последнюю принятую версию без истории всех исполнений."""

    shipment_id: ShipmentIdVO
    shipment_line_id: ShipmentLineIdVO
    shipment_version: int
    shipment_updated_at: datetime
    source_plan_version: int

    def __post_init__(self) -> None:
        """Нормализует время снимка и проверяет собственные идентификаторы и строгие версии."""
        object.__setattr__(
            self,
            "shipment_updated_at",
            normalize_fulfillment_time(self.shipment_updated_at),
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует типизированные ID, целые неотрицательные версии без bool и UTC-время."""
        if (
            not isinstance(self.shipment_id, ShipmentIdVO)
            or not isinstance(self.shipment_line_id, ShipmentLineIdVO)
            or type(self.shipment_version) is not int
            or self.shipment_version < 0
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
        ):
            raise InvalidFulfillmentShipmentProgressRefError(
                "Нужны типизированные ссылки Shipment и строгие неотрицательные версии без bool."
            )
        normalize_fulfillment_time(self.shipment_updated_at)
        if self.shipment_updated_at.utcoffset() != timedelta(0):
            raise InvalidFulfillmentShipmentProgressRefError(
                "Время контрольной точки должно храниться в UTC."
            )
