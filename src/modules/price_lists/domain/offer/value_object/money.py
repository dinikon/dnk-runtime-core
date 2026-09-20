from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re
from src.modules.price_lists.domain.offer.error import InvalidOfferValueError


@dataclass(slots=True, frozen=True)
class MoneyVO:
    """Неотрицательная конечная цена в точности NUMERIC(19,4)."""

    value: Decimal

    def __post_init__(self):
        try:
            raw = Decimal(re.sub(r"\s+", "", str(self.value)).replace(",", "."))
            if not raw.is_finite() or raw < 0 or raw >= Decimal("1000000000000000"):
                raise InvalidOfferValueError("Price is outside NUMERIC(19,4) range.")
            with localcontext() as context:
                context.prec = 24
                normalized = raw.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            if normalized >= Decimal("1000000000000000"):
                raise InvalidOfferValueError("Price is outside NUMERIC(19,4) range.")
            object.__setattr__(self, "value", abs(normalized))
        except (InvalidOperation, ValueError, TypeError):
            raise InvalidOfferValueError("Price must be a finite decimal.") from None


@dataclass(slots=True, frozen=True)
class QuantityVO:
    """Целый неотрицательный остаток в диапазоне PostgreSQL integer."""

    value: int

    def __post_init__(self):
        try:
            raw = Decimal(str(self.value).replace(",", "."))
            if (
                not raw.is_finite()
                or raw < 0
                or raw > 2147483647
                or raw != raw.to_integral_value()
            ):
                raise InvalidOfferValueError(
                    "Quantity must be an integer between 0 and 2147483647."
                )
            object.__setattr__(self, "value", int(raw))
        except (InvalidOperation, ValueError, TypeError):
            raise InvalidOfferValueError("Quantity must be a finite integer.") from None


__all__ = ["MoneyVO", "QuantityVO"]
