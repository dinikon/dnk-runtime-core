from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class SetManualRate:
    """Immutable input for set manual rate."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    pair: CurrencyPair
    rate: Decimal
    effective_date: date

    id: ManualExchangeRateIdVO


__all__ = ["SetManualRate"]
