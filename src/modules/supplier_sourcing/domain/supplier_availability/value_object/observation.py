from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from src.modules.supplier_sourcing.domain.supplier_availability.error import (
    InvalidSupplierAvailabilityValueError,
)


class AvailabilityType(StrEnum):
    """Описывает полноту количественных данных наблюдения."""

    EXACT_QUANTITY = "EXACT_QUANTITY"
    LOWER_BOUND = "LOWER_BOUND"
    STATUS_ONLY = "STATUS_ONLY"
    UNKNOWN = "UNKNOWN"


class AvailabilityStatus(StrEnum):
    """Передаёт статус, сообщённый поставщиком."""

    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    BACKORDER = "BACKORDER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SupplierAvailabilityObservationVO:
    """Сохраняет тип, статус и количество внешнего наблюдения без округления."""

    availability_type: AvailabilityType
    availability_status: AvailabilityStatus
    quantity: Decimal | None

    def __post_init__(self) -> None:
        """Проверяет матрицу совместимости типа, статуса и количества."""
        kind, status, quantity = (
            self.availability_type,
            self.availability_status,
            self.quantity,
        )
        if not isinstance(kind, AvailabilityType) or not isinstance(
            status, AvailabilityStatus
        ):
            raise InvalidSupplierAvailabilityValueError(
                "Нужны типизированные вид и статус наблюдения."
            )
        if kind in (AvailabilityType.EXACT_QUANTITY, AvailabilityType.LOWER_BOUND):
            if (
                not isinstance(quantity, Decimal)
                or not quantity.is_finite()
                or quantity < 0
            ):
                raise InvalidSupplierAvailabilityValueError(
                    "Количественное наблюдение требует конечного неотрицательного Decimal."
                )
            if quantity > 0:
                valid = status is AvailabilityStatus.IN_STOCK
            elif kind is AvailabilityType.EXACT_QUANTITY:
                valid = status in (
                    AvailabilityStatus.OUT_OF_STOCK,
                    AvailabilityStatus.BACKORDER,
                )
            else:
                valid = status is AvailabilityStatus.UNKNOWN
        elif kind is AvailabilityType.STATUS_ONLY:
            valid = quantity is None and status is not AvailabilityStatus.UNKNOWN
        else:
            valid = quantity is None and status is AvailabilityStatus.UNKNOWN
        if not valid:
            raise InvalidSupplierAvailabilityValueError(
                "Статус или количество не соответствуют виду наблюдения."
            )
