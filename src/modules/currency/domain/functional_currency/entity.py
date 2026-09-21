from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyChangeNotAllowed,
)
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class FunctionalCurrencyPeriod:
    """Inclusive functional-currency interval with an independent activation marker."""

    id: FunctionalCurrencyPeriodIdVO
    currency: CurrencyCodeVO
    valid_from: date
    valid_to: date | None
    created_at: datetime
    created_by: EntityIdVO
    reason: str
    activation_emitted_at: datetime | None = None

    def __post_init__(self):
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise CurrencyError("Period end precedes its start.")
        if not self.reason.strip():
            raise CurrencyError("A reason is required.")

    def contains(self, day: date) -> bool:
        return self.valid_from <= day and (
            self.valid_to is None or day <= self.valid_to
        )

    def overlaps(self, other: FunctionalCurrencyPeriod) -> bool:
        return self.valid_from <= (other.valid_to or date.max) and other.valid_from <= (
            self.valid_to or date.max
        )

    def validate_successor(
        self, other: FunctionalCurrencyPeriod, business_date: date
    ) -> None:
        if self.valid_to is not None or other.valid_from <= max(
            self.valid_from, business_date
        ):
            raise FunctionalCurrencyChangeNotAllowed(
                "Append a future period after the last open period."
            )
        if self.currency == other.currency:
            raise FunctionalCurrencyChangeNotAllowed(
                "The new currency equals the last scheduled currency."
            )


__all__ = ["FunctionalCurrencyPeriod"]
