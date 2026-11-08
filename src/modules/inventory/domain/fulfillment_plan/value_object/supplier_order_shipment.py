from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderShipmentError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierShipmentIdVO,
)


@dataclass(frozen=True, slots=True)
class FulfillmentSupplierOrderShipmentRefVO:
    """Фиксирует внешний факт отправки и версию заказа поставщику."""

    shipment_id: FulfillmentSupplierShipmentIdVO
    order_version: int
    shipped_at: datetime

    def __post_init__(self) -> None:
        """Нормализует время внешней отправки в UTC."""
        object.__setattr__(
            self, "shipped_at", normalize_fulfillment_time(self.shipped_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует типизированную ссылку, версию факта и время в UTC."""
        normalize_fulfillment_time(self.shipped_at)
        if (
            not isinstance(self.shipment_id, FulfillmentSupplierShipmentIdVO)
            or type(self.order_version) is not int
            or self.order_version != 3
            or self.shipped_at.utcoffset() != timedelta(0)
        ):
            raise FulfillmentSupplierOrderShipmentError(
                "Нужны ID внешней отправки, версия заказа и время в UTC."
            )
