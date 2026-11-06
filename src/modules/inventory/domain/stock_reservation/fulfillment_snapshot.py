from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationFulfillmentSnapshotError,
)
from src.modules.inventory.domain.stock_reservation.shipment_snapshot import (
    StockReservationShipmentSnapshot,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockReservationFulfillmentSnapshot:
    """Передаёт полный запрос, удержание и погашение для проверки распределения без чужого агрегата."""

    id: StockReservationIdVO
    pool_id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    source_ref: ReservationSourceVO
    base_uom: UomCodeVO
    requested_qty: QuantityVO
    reserved_qty: QuantityVO
    consumed_qty: QuantityVO
    status: StockReservationStatus
    expires_at: datetime | None
    updated_at: datetime
    version: int

    def ensure_valid(self) -> None:
        """Проверяет типы, UTC, строгую версию и согласованность собственных счётчиков со статусом."""
        StockReservationShipmentSnapshot(
            self.id,
            self.pool_id,
            self.key,
            self.source_ref,
            self.base_uom,
            self.reserved_qty,
            self.status,
            self.expires_at,
            self.updated_at,
            self.version,
        ).ensure_valid()
        if (
            not isinstance(self.requested_qty, QuantityVO)
            or self.requested_qty.value.is_zero()
            or not isinstance(self.consumed_qty, QuantityVO)
        ):
            raise InvalidStockReservationFulfillmentSnapshotError(
                "Нужны положительный запрос и неотрицательное погашение QuantityVO."
            )
        accounted = QuantityArithmeticPolicy.add(self.reserved_qty, self.consumed_qty)
        if accounted.value > self.requested_qty.value:
            raise InvalidStockReservationFulfillmentSnapshotError(
                "Удержание и погашение превышают запрос."
            )
        zero, full = (
            self.reserved_qty.value.is_zero(),
            self.reserved_qty == self.requested_qty,
        )
        consumed_zero, consumed_full = (
            self.consumed_qty.value.is_zero(),
            self.consumed_qty == self.requested_qty,
        )
        if (
            (
                self.status is StockReservationStatus.PENDING
                and (not zero or not consumed_zero)
            )
            or (
                self.status is StockReservationStatus.PARTIALLY_RESERVED
                and (zero or full or not consumed_zero)
            )
            or (
                self.status is StockReservationStatus.RESERVED
                and (not full or not consumed_zero)
            )
            or (
                self.status is StockReservationStatus.PARTIALLY_CONSUMED
                and (consumed_zero or consumed_full)
            )
            or (
                self.status is StockReservationStatus.CONSUMED
                and (not consumed_full or not zero)
            )
            or (
                self.status
                in (StockReservationStatus.RELEASED, StockReservationStatus.EXPIRED)
                and (not zero or consumed_full)
            )
        ):
            raise InvalidStockReservationFulfillmentSnapshotError(
                "Статус не соответствует запросу, удержанию и погашению снимка."
            )
