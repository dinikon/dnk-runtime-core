from dataclasses import dataclass
from datetime import datetime
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.provider_rate.value_object.id import ProviderRateIdVO


@dataclass(frozen=True, slots=True)
class ProviderRate(RateRecord):
    """Immutable values of one provider rate revision."""

    id: ProviderRateIdVO
    created_at: datetime | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None


__all__ = ["ProviderRate"]
