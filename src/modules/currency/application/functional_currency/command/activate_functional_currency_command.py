from dataclasses import dataclass
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ActivateFunctionalCurrencyCommand:
    """Immutable input for activate functional currency."""

    tenant_id: EntityIdVO
    period_id: FunctionalCurrencyPeriodIdVO


__all__ = ["ActivateFunctionalCurrencyCommand"]
