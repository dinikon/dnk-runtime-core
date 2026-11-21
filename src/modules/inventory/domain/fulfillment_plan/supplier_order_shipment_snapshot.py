from dataclasses import dataclass

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderConfirmationError,
    FulfillmentSupplierOrderShipmentError,
)
from src.modules.inventory.domain.fulfillment_plan.supplier_order_assignment_snapshot import (
    SupplierOrderConfirmationSnapshot,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOrderLineIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_order_shipment import (
    FulfillmentSupplierOrderShipmentRefVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


@dataclass(frozen=True, slots=True)
class SupplierOrderShipmentSnapshot:
    """Передаёт внешнюю отправку по всему положительному подтверждению поставщика."""

    confirmation: SupplierOrderConfirmationSnapshot
    shipment: FulfillmentSupplierOrderShipmentRefVO
    shipped_quantities: tuple[tuple[FulfillmentSupplierOrderLineIdVO, QuantityVO], ...]

    def ensure_valid(self) -> None:
        """Сверяет основание, хронологию и полноту отправленных количеств."""
        if (
            not isinstance(self.confirmation, SupplierOrderConfirmationSnapshot)
            or not isinstance(self.shipment, FulfillmentSupplierOrderShipmentRefVO)
            or not isinstance(self.shipped_quantities, tuple)
            or any(
                not isinstance(row, tuple)
                or len(row) != 2
                or not isinstance(row[0], FulfillmentSupplierOrderLineIdVO)
                or not isinstance(row[1], QuantityVO)
                for row in self.shipped_quantities
            )
        ):
            raise FulfillmentSupplierOrderShipmentError(
                "Внешняя отправка требует типизированные основание, ссылку и строки."
            )
        try:
            self.confirmation.ensure_valid()
        except FulfillmentSupplierOrderConfirmationError as exc:
            raise FulfillmentSupplierOrderShipmentError(
                "Внешняя отправка требует полное подтверждение заказа."
            ) from exc
        self.shipment.ensure_valid()
        confirmed_quantities = self.confirmation.confirmed_quantities
        confirmed = self.confirmation.confirmation
        if (
            confirmed_quantities is None
            or self.shipment.order_version != confirmed.order_version + 1
            or self.shipment.shipped_at < confirmed.confirmed_at
        ):
            raise FulfillmentSupplierOrderShipmentError(
                "Отправка следует за подтверждением с явными количествами."
            )
        quantities = dict(self.shipped_quantities)
        if len(quantities) != len(self.shipped_quantities) or quantities != {
            line_id: quantity
            for line_id, quantity in confirmed_quantities
            if not quantity.value.is_zero()
        }:
            raise FulfillmentSupplierOrderShipmentError(
                "Отправленные количества должны полностью покрывать подтверждение."
            )
