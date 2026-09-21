from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ScheduleFunctionalCurrencyChange:
    """Immutable input for schedule functional currency change."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    currency: CurrencyCodeVO
    effective_from: date
    reason: str

    id: FunctionalCurrencyPeriodIdVO


__all__ = ["ScheduleFunctionalCurrencyChange"]
