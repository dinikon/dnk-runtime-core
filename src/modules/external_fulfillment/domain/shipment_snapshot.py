from dataclasses import dataclass

from src.modules.external_fulfillment.domain.confirmation_snapshot import (
    SupplierFulfillmentConfirmationSnapshot,
)
from src.modules.external_fulfillment.domain.value_object.shipment import (
    SupplierFulfillmentShipmentLineVO,
    SupplierFulfillmentShipmentVO,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentShipmentSnapshot:
    """Передаёт факт внешней отправки вместе с историческим подтверждением."""

    confirmation: SupplierFulfillmentConfirmationSnapshot
    shipment: SupplierFulfillmentShipmentVO
    order_version: int
    lines: tuple[SupplierFulfillmentShipmentLineVO, ...]
