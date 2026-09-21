from dataclasses import dataclass
from datetime import date
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.money import Money


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    """One dated calculation, optionally targeting the functional currency."""

    money: Money
    business_date: date
    target: CurrencyCodeVO | None = None
    purpose: ConversionPurpose = ConversionPurpose.CALCULATION
    precision: int | None = None


__all__ = ["ConversionRequest"]
