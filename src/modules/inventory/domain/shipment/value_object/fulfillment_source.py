from dataclasses import dataclass

from src.modules.inventory.domain.fulfillment_plan.value_object.identifier import (
    FulfillmentPlanIdVO,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentFulfillmentSourceError,
)


@dataclass(frozen=True, slots=True)
class ShipmentFulfillmentSourceVO:
    """Сохраняет ID и версию основания, не включая чужой агрегат в отгрузку."""

    plan_id: FulfillmentPlanIdVO
    plan_version: int

    def __post_init__(self) -> None:
        """Проверяет собственные ID и целую неотрицательную версию без bool."""
        if (
            not isinstance(self.plan_id, FulfillmentPlanIdVO)
            or type(self.plan_version) is not int
            or self.plan_version < 0
        ):
            raise InvalidShipmentFulfillmentSourceError(
                "Нужны FulfillmentPlanIdVO и целая неотрицательная версия без bool."
            )
