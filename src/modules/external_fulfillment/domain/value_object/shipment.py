from dataclasses import dataclass
from datetime import datetime

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.time import (
    normalize_supplier_fulfillment_time,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
    SupplierFulfillmentShipmentIdVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentShipmentVO:
    """Хранит идентичность, время и сведения об отправке поставщика."""

    id: SupplierFulfillmentShipmentIdVO
    shipped_at: datetime
    carrier_id: str | None = None
    tracking_number: str | None = None

    def __post_init__(self) -> None:
        """Проверяет ID и переданные реквизиты, нормализует время в UTC."""
        if not isinstance(self.id, SupplierFulfillmentShipmentIdVO) or any(
            value is not None and (not isinstance(value, str) or not value.strip())
            for value in (self.carrier_id, self.tracking_number)
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужен ID внешней отправки и непустые переданные реквизиты."
            )
        object.__setattr__(
            self, "shipped_at", normalize_supplier_fulfillment_time(self.shipped_at)
        )


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentShipmentLineVO:
    """Фиксирует положительное отгруженное количество по строке заказа."""

    line_id: SupplierFulfillmentLineIdVO
    quantity: SupplierFulfillmentQuantityVO

    def __post_init__(self) -> None:
        """Проверяет типизированную строку и положительное количество."""
        if (
            not isinstance(self.line_id, SupplierFulfillmentLineIdVO)
            or not isinstance(self.quantity, SupplierFulfillmentQuantityVO)
            or self.quantity.value.is_zero()
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Строка отправки требует ID и положительное количество."
            )
