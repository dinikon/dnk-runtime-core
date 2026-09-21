from dataclasses import dataclass
from datetime import date
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ResolveExchangeRateQuery:
    """Immutable selection criteria for resolve exchange rate."""

    tenant_id: EntityIdVO
    source: CurrencyCodeVO
    target: CurrencyCodeVO
    business_date: date


__all__ = ["ResolveExchangeRateQuery"]
