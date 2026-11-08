from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderConfirmationError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)


@dataclass(frozen=True, slots=True)
class FulfillmentSupplierOrderConfirmationRefVO:
    """Фиксирует версию и время подтверждения ранее закреплённого внешнего заказа."""

    order_version: int
    requested_at: datetime
    confirmed_at: datetime

    def __post_init__(self) -> None:
        """Нормализует оба времени и проверяет хронологию ответа."""
        object.__setattr__(
            self, "requested_at", normalize_fulfillment_time(self.requested_at)
        )
        object.__setattr__(
            self, "confirmed_at", normalize_fulfillment_time(self.confirmed_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует версию полного подтверждения и время ответа после запроса в UTC."""
        normalize_fulfillment_time(self.requested_at)
        normalize_fulfillment_time(self.confirmed_at)
        if (
            type(self.order_version) is not int
            or self.order_version != 2
            or self.requested_at.utcoffset() != timedelta(0)
            or self.confirmed_at.utcoffset() != timedelta(0)
            or self.confirmed_at < self.requested_at
        ):
            raise FulfillmentSupplierOrderConfirmationError(
                "Нужны версия полного подтверждения и согласованные времена запроса и ответа в UTC."
            )
