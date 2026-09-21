from __future__ import annotations
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from decimal import Context, MAX_EMAX, MIN_EMIN
from fractions import Fraction
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.money_errors import (
    CurrencyMismatchError,
    InvalidMoneyError,
    InexactMoneyDivisionError,
)


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
        with localcontext(Context(Emax=MAX_EMAX, Emin=MIN_EMIN)) as context:
            context.prec = max(context.prec, self._sum_precision(other.amount))
            return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._same_currency(other)
        with localcontext(Context(Emax=MAX_EMAX, Emin=MIN_EMIN)) as context:
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
        with localcontext(Context(Emax=MAX_EMAX, Emin=MIN_EMIN)) as context:
            context.prec = max(
                context.prec,
                len(self.amount.as_tuple().digits) + len(scalar.as_tuple().digits),
            )
            return Money(self.amount * scalar, self.currency)

    __rmul__ = __mul__

    def __truediv__(self, scalar: Decimal | int) -> Money:
        """Divide exactly, rejecting a repeating decimal without rounding."""
        scalar = exact_decimal(scalar)
        if not scalar:
            raise InvalidMoneyError("Cannot divide money by zero.")
        fraction = Fraction(self.amount) / Fraction(scalar)
        denominator = fraction.denominator
        twos = fives = 0
        while denominator % 2 == 0:
            denominator //= 2
            twos += 1
        while denominator % 5 == 0:
            denominator //= 5
            fives += 1
        if denominator != 1:
            raise InexactMoneyDivisionError(
                "Repeating decimal: use divide with explicit precision and rounding."
            )
        scale = max(twos, fives)
        coefficient = fraction.numerator * 2 ** (scale - twos) * 5 ** (scale - fives)
        digits = Decimal(abs(coefficient)).as_tuple().digits
        return Money(Decimal((int(coefficient < 0), digits, -scale)), self.currency)

    def divide(self, scalar: Decimal | int, *, precision: int, rounding: str) -> Money:
        """Divide with an explicitly chosen number of significant digits."""
        scalar = exact_decimal(scalar)
        if not scalar:
            raise InvalidMoneyError("Cannot divide money by zero.")
        if type(precision) is not int or precision < 1:
            raise InvalidMoneyError("Calculation precision must be a positive integer.")
        try:
            context = Context(prec=precision, rounding=rounding)
        except (TypeError, ValueError):
            raise InvalidMoneyError("Invalid calculation rounding mode.") from None
        with localcontext(context):
            return Money(self.amount / scalar, self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def is_positive(self) -> bool:
        return self.amount > 0


__all__ = ["Money"]
