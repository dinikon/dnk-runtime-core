from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_reference import (
    FulfillmentSupplierReferenceVO,
)
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderAssignmentError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOrderIdVO,
    FulfillmentSupplierOrderLineIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_quantity_terms import (
    FulfillmentSupplierQuantityTermsVO,
)


@dataclass(frozen=True, slots=True)
class FulfillmentSupplierOrderAssignmentRefVO:
    """Закрепляет плановую строку за одним внешним заказом и его строкой."""

    order_id: FulfillmentSupplierOrderIdVO
    line_id: FulfillmentSupplierOrderLineIdVO
    supplier: FulfillmentSupplierReferenceVO
    order_version: int
    source_plan_version: int
    assigned_at: datetime
    quantity_terms: FulfillmentSupplierQuantityTermsVO | None = None

    def __post_init__(self) -> None:
        """Нормализует момент назначения и проверяет собственные ссылки и версии."""
        object.__setattr__(
            self, "assigned_at", normalize_fulfillment_time(self.assigned_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует номинальные ссылки, строгие неотрицательные версии и время в UTC."""
        if (
            not isinstance(self.order_id, FulfillmentSupplierOrderIdVO)
            or not isinstance(self.line_id, FulfillmentSupplierOrderLineIdVO)
            or not isinstance(self.supplier, FulfillmentSupplierReferenceVO)
            or type(self.order_version) is not int
            or self.order_version < 0
            or type(self.source_plan_version) is not int
            or self.source_plan_version < 0
            or (
                self.quantity_terms is not None
                and not isinstance(
                    self.quantity_terms, FulfillmentSupplierQuantityTermsVO
                )
            )
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Нужны типизированные ссылки внешнего заказа и целые версии назначения."
            )
        normalize_fulfillment_time(self.assigned_at)
        if self.assigned_at.utcoffset() != timedelta(0):
            raise FulfillmentSupplierOrderAssignmentError(
                "Время закрепления должно храниться в UTC."
            )
