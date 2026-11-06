from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentReservationReleaseRefError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.reservation_ref import (
    FulfillmentReservationRefVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)


@dataclass(frozen=True, slots=True)
class FulfillmentReservationReleaseRefVO:
    """Сохраняет прежнее подтверждение и проверенное закрытие резерва без копирования чужого агрегата."""

    confirmation: FulfillmentReservationRefVO
    closed_version: int
    closed_status: StockReservationStatus
    closed_at: datetime
    released_at: datetime

    def __post_init__(self) -> None:
        """Нормализует явные даты в UTC и проверяет собственные значения и хронологию."""
        object.__setattr__(
            self, "closed_at", normalize_fulfillment_time(self.closed_at)
        )
        object.__setattr__(
            self, "released_at", normalize_fulfillment_time(self.released_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует закрытие RELEASED/EXPIRED более новой строгой версией и последовательность дат подтверждения/закрытия/снятия."""
        if (
            not isinstance(self.confirmation, FulfillmentReservationRefVO)
            or type(self.closed_version) is not int
            or not isinstance(self.closed_status, StockReservationStatus)
            or self.closed_status
            not in (StockReservationStatus.RELEASED, StockReservationStatus.EXPIRED)
        ):
            raise InvalidFulfillmentReservationReleaseRefError(
                "Нужны прежнее подтверждение, строгая версия без bool и статус RELEASED/EXPIRED."
            )
        self.confirmation.ensure_valid()
        normalize_fulfillment_time(self.closed_at)
        normalize_fulfillment_time(self.released_at)
        if (
            self.closed_version <= self.confirmation.version
            or self.closed_at.utcoffset() != timedelta(0)
            or self.released_at.utcoffset() != timedelta(0)
            or not self.confirmation.confirmed_at <= self.closed_at <= self.released_at
        ):
            raise InvalidFulfillmentReservationReleaseRefError(
                "Закрытие требует более новую версию и UTC-хронологию подтверждение → закрытие → снятие."
            )
