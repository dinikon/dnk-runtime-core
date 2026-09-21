from dataclasses import dataclass
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetRateHistoryQuery:
    """Input for get rate history."""

    tenant_id: EntityIdVO
    provider: ProviderCode
    pair: CurrencyPair | None = None
    limit: int = 100
    offset: int = 0


__all__ = ["GetRateHistoryQuery"]
