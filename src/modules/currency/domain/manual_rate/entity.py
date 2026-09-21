from dataclasses import dataclass
from datetime import datetime
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ManualExchangeRate(RateRecord):
    """Immutable values of one manual rate revision."""

    id: ManualExchangeRateIdVO
    created_at: datetime | None = None
    created_by: EntityIdVO | None = None


__all__ = ["ManualExchangeRate"]
