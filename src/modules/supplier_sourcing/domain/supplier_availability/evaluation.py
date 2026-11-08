from dataclasses import dataclass

from src.modules.supplier_sourcing.domain.supplier_availability.value_object.observation import (
    SupplierAvailabilityObservationVO,
)


@dataclass(frozen=True, slots=True)
class SupplierAvailabilityEvaluation:
    """Результат оценки наблюдения с отдельным признаком блокировки из-за TTL."""

    observation: SupplierAvailabilityObservationVO
    is_stale: bool
    automatic_sale_blocked: bool
