from dataclasses import dataclass

from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationExecutionSnapshotError,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockReservationExecutionSnapshot:
    """Передаёт идентичность, привязку и версию обязательства без его жизненного цикла и счётчиков."""

    id: StockReservationIdVO
    pool_id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    base_uom: UomCodeVO
    version: int

    def ensure_valid(self) -> None:
        """Требует типизированную область, известную единицу и строгую неотрицательную версию."""
        if (
            not isinstance(self.id, StockReservationIdVO)
            or not isinstance(self.pool_id, AvailabilityPoolIdVO)
            or not isinstance(self.key, AvailabilityPoolKeyVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockReservationExecutionSnapshotError(
                "Нужен типизированный снимок привязки и версии резерва."
            )
        get_uom(self.base_uom)
