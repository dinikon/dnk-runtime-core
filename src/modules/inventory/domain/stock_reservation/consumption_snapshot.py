from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationConsumptionSnapshotError,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockReservationConsumptionSnapshot:
    """Фиксирует погашение одного резерва по явным строкам исполнения и версии обязательства."""

    execution_id: StockExecutionIdVO
    execution_line_ids: tuple[StockExecutionLineIdVO, ...]
    reservation_id: StockReservationIdVO
    reservation_version: int
    pool_id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    consumed_at: datetime

    def ensure_valid(self) -> None:
        """Проверяет типы, положительную величину, UTC-факт и непустые уникальные ID строк."""
        if (
            not isinstance(self.execution_id, StockExecutionIdVO)
            or not isinstance(self.reservation_id, StockReservationIdVO)
            or type(self.reservation_version) is not int
            or self.reservation_version < 0
            or not isinstance(self.pool_id, AvailabilityPoolIdVO)
            or not isinstance(self.key, AvailabilityPoolKeyVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.consumed_at, datetime)
            or self.consumed_at.utcoffset() != timedelta(0)
            or not isinstance(self.execution_line_ids, tuple)
            or not self.execution_line_ids
            or not all(
                isinstance(identifier, StockExecutionLineIdVO)
                for identifier in self.execution_line_ids
            )
        ):
            raise InvalidStockReservationConsumptionSnapshotError(
                "Нужен типизированный снимок положительного погашения с версией, UTC-временем и ID строк."
            )
        get_uom(self.base_uom)
        if len(set(self.execution_line_ids)) != len(self.execution_line_ids):
            raise InvalidStockReservationConsumptionSnapshotError(
                "Повтор ID строки внутри погашения запрещён."
            )
