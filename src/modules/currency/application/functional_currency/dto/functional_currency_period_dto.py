from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class FunctionalCurrencyPeriodDTO:
    """Immutable functional currency application result."""

    id: EntityIdVO
    currency: CurrencyCodeVO
    valid_from: date
    valid_to: date | None
    created_at: datetime
    created_by: EntityIdVO
    reason: str
    activation_emitted_at: datetime | None = None

    @classmethod
    def from_entity(
        cls, value: FunctionalCurrencyPeriod
    ) -> "FunctionalCurrencyPeriodDTO":
        return cls(
            id=value.id,
            currency=value.currency,
            valid_from=value.valid_from,
            valid_to=value.valid_to,
            created_at=value.created_at,
            created_by=value.created_by,
            reason=value.reason,
            activation_emitted_at=value.activation_emitted_at,
        )


__all__ = ["FunctionalCurrencyPeriodDTO"]
