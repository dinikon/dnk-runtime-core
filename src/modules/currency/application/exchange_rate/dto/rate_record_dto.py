from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.manual_rate.entity import ManualExchangeRate
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.provider_rate.entity import ProviderRate
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class RateRecordDTO:
    """A stored revision with explicit provenance for history and edit results."""

    id: EntityIdVO
    pair: CurrencyPair
    rate: Decimal
    effective_date: date
    provider_code: ProviderCode
    revision: int
    is_current: bool
    calculated_date: date | None
    created_at: datetime | None
    created_by: EntityIdVO | None

    @classmethod
    def from_entity(cls, rate: RateRecord) -> "RateRecordDTO":
        return cls(
            rate.id,
            rate.pair,
            rate.rate,
            rate.effective_date,
            rate.provider_code,
            rate.revision,
            rate.is_current,
            rate.calculated_date,
            (
                rate.created_at
                if isinstance(rate, (ManualExchangeRate, ProviderRate))
                else None
            ),
            rate.created_by if isinstance(rate, ManualExchangeRate) else None,
        )


__all__ = ["RateRecordDTO"]
