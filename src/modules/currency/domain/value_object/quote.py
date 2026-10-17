from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.currency.domain.error import InvalidExchangeRateError


@dataclass(frozen=True, slots=True)
class ExchangeRateQuoteVO:
    """Котировка исходной валюты в UAH за одну единицу."""

    currency: CurrencyVO
    rate: Decimal

    def __post_init__(self) -> None:
        """Нормализует коэффициент в точности NUMERIC(38,18)."""
        if not isinstance(self.currency, CurrencyVO) or not isinstance(
            self.rate, Decimal
        ):
            raise InvalidExchangeRateError("CurrencyVO and Decimal are required.")
        limit = Decimal("1e20")
        if not self.rate.is_finite() or self.rate <= 0 or self.rate >= limit:
            raise InvalidExchangeRateError("Rate is outside NUMERIC(38,18).")
        try:
            with localcontext(Context(prec=60, rounding=ROUND_HALF_UP)):
                rate = self.rate.quantize(Decimal("1e-18"))
        except InvalidOperation as exc:
            raise InvalidExchangeRateError("Rate cannot be rounded.") from exc
        if rate <= 0 or rate >= limit:
            raise InvalidExchangeRateError("Rounded rate is outside NUMERIC(38,18).")
        object.__setattr__(self, "rate", rate)
