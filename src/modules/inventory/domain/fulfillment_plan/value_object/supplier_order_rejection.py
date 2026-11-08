from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderRejectionError,
)
from src.modules.inventory.domain.fulfillment_plan.time import (
    normalize_fulfillment_time,
)


@dataclass(frozen=True, slots=True)
class FulfillmentSupplierOrderRejectionRefVO:
    """Фиксирует версию и время явного отказа по закреплённому внешнему заказу."""

    order_version: int
    requested_at: datetime
    rejected_at: datetime

    def __post_init__(self) -> None:
        """Нормализует время запроса и отказа в UTC."""
        object.__setattr__(
            self, "requested_at", normalize_fulfillment_time(self.requested_at)
        )
        object.__setattr__(
            self, "rejected_at", normalize_fulfillment_time(self.rejected_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует версию окончательного отказа и хронологию ответа в UTC."""
        normalize_fulfillment_time(self.requested_at)
        normalize_fulfillment_time(self.rejected_at)
        if (
            type(self.order_version) is not int
            or self.order_version != 2
            or self.requested_at.utcoffset() != timedelta(0)
            or self.rejected_at.utcoffset() != timedelta(0)
            or self.rejected_at < self.requested_at
        ):
            raise FulfillmentSupplierOrderRejectionError(
                "Нужны версия отказа и согласованное время запроса и отказа в UTC."
            )
