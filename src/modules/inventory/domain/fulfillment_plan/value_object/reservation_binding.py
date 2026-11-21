from dataclasses import dataclass

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentReservationBindingError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_id import (
    FulfillmentAllocationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)


@dataclass(frozen=True, slots=True)
class FulfillmentReservationBindingVO:
    """Назначает распределению явно выбранные ID и ожидаемую версию существующего резерва."""

    allocation_id: FulfillmentAllocationIdVO
    reservation_id: StockReservationIdVO
    reservation_version: int

    def __post_init__(self) -> None:
        """Требует типизированные идентификаторы и целую неотрицательную версию без bool."""
        if (
            not isinstance(self.allocation_id, FulfillmentAllocationIdVO)
            or not isinstance(self.reservation_id, StockReservationIdVO)
            or type(self.reservation_version) is not int
            or self.reservation_version < 0
        ):
            raise InvalidFulfillmentReservationBindingError(
                "Нужны ID распределения/резерва и строгая неотрицательная версия."
            )
