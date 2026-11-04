from dataclasses import dataclass

from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidReservationExecutionBindingError,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)


@dataclass(frozen=True, slots=True)
class ReservationExecutionBindingVO:
    """Явно назначает всю фактическую строку одному резерву без отдельного пользовательского количества."""

    execution_line_id: StockExecutionLineIdVO
    reservation_id: StockReservationIdVO

    def __post_init__(self) -> None:
        """Требует типизированные ссылки фактической строки и обязательства."""
        if not isinstance(
            self.execution_line_id, StockExecutionLineIdVO
        ) or not isinstance(self.reservation_id, StockReservationIdVO):
            raise InvalidReservationExecutionBindingError(
                "Нужны ID фактической строки и резерва."
            )
