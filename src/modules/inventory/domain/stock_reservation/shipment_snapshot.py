from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationShipmentSnapshotError,
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
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockReservationShipmentSnapshot:
    """Передаёт основание, текущее удержание и срок резерва для планирования без чужого корня."""

    id: StockReservationIdVO
    pool_id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    source_ref: ReservationSourceVO
    base_uom: UomCodeVO
    reserved_qty: QuantityVO
    status: StockReservationStatus
    expires_at: datetime | None
    updated_at: datetime
    version: int

    def ensure_valid(self) -> None:
        """Проверяет типы, UTC-время, версию и локально проверяемую совместимость удержания со статусом."""
        if (
            not isinstance(self.id, StockReservationIdVO)
            or not isinstance(self.pool_id, AvailabilityPoolIdVO)
            or not isinstance(self.key, AvailabilityPoolKeyVO)
            or not isinstance(self.source_ref, ReservationSourceVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.reserved_qty, QuantityVO)
            or not isinstance(self.status, StockReservationStatus)
            or not isinstance(self.updated_at, datetime)
            or self.updated_at.utcoffset() != timedelta(0)
            or (
                self.expires_at is not None
                and (
                    not isinstance(self.expires_at, datetime)
                    or self.expires_at.utcoffset() != timedelta(0)
                )
            )
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockReservationShipmentSnapshotError(
                "Нужен типизированный снимок текущего удержания с UTC-временем и версией."
            )
        get_uom(self.base_uom)
        zero = self.reserved_qty.value.is_zero()
        if (
            (
                (
                    self.status is StockReservationStatus.PENDING
                    or self.status.is_terminal
                )
                and not zero
            )
            or (
                self.status
                in (
                    StockReservationStatus.RESERVED,
                    StockReservationStatus.PARTIALLY_RESERVED,
                )
                and zero
            )
            or (
                self.status is StockReservationStatus.EXPIRED
                and (self.expires_at is None or self.updated_at < self.expires_at)
            )
        ):
            raise InvalidStockReservationShipmentSnapshotError(
                "Статус не соответствует собственным полям снимка резерва."
            )
