from __future__ import annotations
from decimal import Context, MAX_EMAX, MIN_EMIN
from decimal import Decimal
from decimal import localcontext
from src.modules.currency.domain.conversion.error import CurrencyPrecisionUndefined
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.shared.domain.value_object.money import Money


class MoneyQuantizer:
    """Apply the explicitly selected calculation, booking or display precision."""

    def quantize(
        self,
        money: Money,
        *,
        minor_units: int | None,
        rounding_mode: RoundingMode,
        purpose: ConversionPurpose,
        precision: int | None = None,
    ) -> Money:
        if precision is not None and (type(precision) is not int or precision < 0):
            raise CurrencyPrecisionUndefined("Invalid explicit precision.")
        if purpose == ConversionPurpose.CALCULATION:
            return money
        minor_units = precision if precision is not None else minor_units
        if minor_units is None and purpose == ConversionPurpose.DISPLAY:
            return money
        if minor_units is None:
            raise CurrencyPrecisionUndefined(
                f"No minor units configured for {money.currency}."
            )
        if precision is None and (
            type(minor_units) is not int or not 0 <= minor_units <= 9
        ):
            raise CurrencyPrecisionUndefined("Invalid minor units.")
        with localcontext(Context(Emax=MAX_EMAX, Emin=MIN_EMIN)) as context:
            context.prec = max(
                38,
                money.amount.adjusted() + minor_units + 4,
                len(money.amount.as_tuple().digits) + 4,
            )
            return Money(
                money.amount.quantize(
                    Decimal(1).scaleb(-minor_units), rounding=rounding_mode.value
                ),
                money.currency,
            )


__all__ = ["MoneyQuantizer"]
