from __future__ import annotations
from decimal import Context, MAX_EMAX, MIN_EMIN
from decimal import localcontext
from src.modules.currency.domain.exchange_rate.value_object.rate_quote import RateQuote
from src.modules.shared.domain.value_object.money import Money


class ConversionCalculator:
    """Multiply the original amount by a quote without intermediate rounding."""

    def convert(self, money: Money, quote: RateQuote) -> Money:
        if money.currency != quote.pair.source:
            from src.modules.shared.domain.value_object.money_errors import (
                CurrencyMismatchError,
            )

            raise CurrencyMismatchError("Money does not match quote source.")
        with localcontext(Context(Emax=MAX_EMAX, Emin=MIN_EMIN)) as context:
            context.prec = max(
                38,
                len(money.amount.as_tuple().digits) + len(quote.rate.as_tuple().digits),
            )
            return Money(money.amount * quote.rate, quote.pair.target)


__all__ = ["ConversionCalculator"]
