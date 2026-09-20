from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from .currency import CurrencyCodeVO
from .money_errors import CurrencyMismatchError, InvalidMoneyError


def exact_decimal(value: Decimal | int) -> Decimal:
    if type(value) is int:
        value = Decimal(value)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise InvalidMoneyError(
            "Expected a finite Decimal or integer; floats are not accepted."
        )
    return value


@dataclass(frozen=True, slots=True)
class Money:
    """Monetary value with no implicit conversion or quantization."""

    amount: Decimal
    currency: CurrencyCodeVO

    def __post_init__(self):
        object.__setattr__(self, "amount", exact_decimal(self.amount))
        if not isinstance(self.currency, CurrencyCodeVO):
            raise InvalidMoneyError("Money requires a CurrencyCodeVO.")

    def _same_currency(self, other: Money):
        if not isinstance(other, Money):
            raise TypeError("Expected Money.")
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Cannot combine {self.currency} and {other.currency}."
            )

    def __add__(self, other: Money) -> Money:
        self._same_currency(other)
        with localcontext() as context:
            context.prec = max(context.prec, self._sum_precision(other.amount))
            return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._same_currency(other)
        with localcontext() as context:
            context.prec = max(context.prec, self._sum_precision(other.amount))
            return Money(self.amount - other.amount, self.currency)

    def _sum_precision(self, other: Decimal) -> int:
        return (
            max(self.amount.adjusted(), other.adjusted())
            - min(self.amount.as_tuple().exponent, other.as_tuple().exponent)
            + 2
        )

    def __mul__(self, scalar: Decimal | int) -> Money:
        scalar = exact_decimal(scalar)
        with localcontext() as context:
            context.prec = max(
                context.prec,
                len(self.amount.as_tuple().digits) + len(scalar.as_tuple().digits),
            )
            return Money(self.amount * scalar, self.currency)

    __rmul__ = __mul__

    def __truediv__(self, scalar: Decimal | int) -> Money:
        scalar = exact_decimal(scalar)
        if not scalar:
            raise InvalidMoneyError("Cannot divide money by zero.")
        return Money(self.amount / scalar, self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def is_positive(self) -> bool:
        return self.amount > 0


__all__ = ["Money"]
