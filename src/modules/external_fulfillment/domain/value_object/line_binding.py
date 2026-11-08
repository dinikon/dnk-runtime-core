from dataclasses import dataclass

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
)
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalFulfillmentAllocationIdVO,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentLineBindingVO:
    """Назначает внешний ID строки явно выбранному распределению."""

    allocation_id: ExternalFulfillmentAllocationIdVO
    line_id: SupplierFulfillmentLineIdVO

    def __post_init__(self) -> None:
        """Требует отдельные номинальные идентификаторы распределения и строки."""
        if not isinstance(
            self.allocation_id, ExternalFulfillmentAllocationIdVO
        ) or not isinstance(self.line_id, SupplierFulfillmentLineIdVO):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны идентификаторы распределения и строки внешнего заказа."
            )
