from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentReservationRefError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)


@dataclass(frozen=True, slots=True)
class FulfillmentReservationRefVO:
    """Сохраняет ID и проверенную версию резерва с моментом подтверждения без копирования чужого состояния."""

    reservation_id: StockReservationIdVO
    version: int
    confirmed_at: datetime

    def __post_init__(self) -> None:
        """Нормализует момент и проверяет собственную ссылку и строгую неотрицательную версию."""
        object.__setattr__(
            self, "confirmed_at", normalize_fulfillment_time(self.confirmed_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Проверяет локальные типы и UTC без загрузки или переоценки резерва."""
        if (
            not isinstance(self.reservation_id, StockReservationIdVO)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidFulfillmentReservationRefError(
                "Нужны StockReservationIdVO и целая неотрицательная версия без bool."
            )
        normalize_fulfillment_time(self.confirmed_at)
        if self.confirmed_at.utcoffset() != timedelta(0):
            raise InvalidFulfillmentReservationRefError(
                "Момент подтверждения должен храниться в UTC."
            )
